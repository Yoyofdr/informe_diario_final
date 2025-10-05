"""
Modelos para el sistema de suscripciones y pagos con Flow
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid


class Plan(models.Model):
    """Planes de suscripción disponibles"""
    PLAN_TYPES = [
        ('individual', 'Plan Individual'),
        ('organizacion', 'Plan Organización'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    price = models.IntegerField(help_text="Precio en CLP")
    description = models.TextField()
    max_users = models.IntegerField(default=1, help_text="Máximo de usuarios para este plan")
    
    # Características del plan
    features = models.JSONField(default=dict, help_text="Características del plan en formato JSON")
    
    # Flow IDs
    flow_plan_id = models.CharField(max_length=100, blank=True, help_text="ID del plan en Flow")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
        verbose_name = "Plan de Suscripción"
        verbose_name_plural = "Planes de Suscripción"
    
    def __str__(self):
        return f"{self.name} - ${self.price:,} CLP"


class Subscription(models.Model):
    """Suscripción de un usuario a un plan"""
    STATUS_CHOICES = [
        ('trial', 'Período de Prueba'),
        ('active', 'Activa'),
        ('past_due', 'Pago Pendiente'),
        ('canceled', 'Cancelada'),
        ('expired', 'Expirada'),
    ]
    
    # Identificador único
    subscription_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Relaciones
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    
    # Fechas importantes
    trial_start = models.DateTimeField(auto_now_add=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Flow IDs
    flow_customer_id = models.CharField(max_length=100, blank=True, help_text="ID del cliente en Flow")
    flow_subscription_id = models.CharField(max_length=100, blank=True, help_text="ID de la suscripción en Flow")
    
    # Información de pago
    payment_method_added = models.BooleanField(default=False, help_text="Si el usuario agregó método de pago")
    last_payment_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Suscripción"
        verbose_name_plural = "Suscripciones"
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Configurar trial_end si es nueva suscripción
        if not self.pk and not self.trial_end:
            self.trial_end = timezone.now() + timedelta(days=7)
        
        # Configurar período actual si está activa
        if self.status == 'active' and not self.current_period_end:
            self.current_period_start = timezone.now()
            self.current_period_end = timezone.now() + timedelta(days=30)
            self.next_payment_date = self.current_period_end
        
        super().save(*args, **kwargs)
    
    @property
    def is_trial(self):
        """Verifica si está en período de prueba"""
        return self.status == 'trial' and timezone.now() < self.trial_end
    
    @property
    def is_active(self):
        """Verifica si la suscripción está activa (incluye trial)"""
        return self.status in ['trial', 'active'] and (
            self.is_trial or 
            (self.current_period_end and timezone.now() < self.current_period_end)
        )
    
    @property
    def days_until_trial_end(self):
        """Días restantes del período de prueba"""
        if self.is_trial:
            delta = self.trial_end - timezone.now()
            return max(0, delta.days)
        return 0
    
    @property
    def requires_payment_method(self):
        """Verifica si necesita agregar método de pago"""
        return self.is_trial and not self.payment_method_added
    
    def cancel(self):
        """Cancela la suscripción"""
        self.status = 'canceled'
        self.canceled_at = timezone.now()
        self.save()
    
    def activate(self):
        """Activa la suscripción después del trial"""
        self.status = 'active'
        self.current_period_start = timezone.now()
        self.current_period_end = timezone.now() + timedelta(days=30)
        self.next_payment_date = self.current_period_end
        self.save()


class Payment(models.Model):
    """Registro de pagos realizados"""
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('refunded', 'Reembolsado'),
    ]
    
    # Identificador único
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Relaciones
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    
    # Información del pago
    amount = models.IntegerField(help_text="Monto en CLP")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    
    # Flow IDs
    flow_order_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    flow_token = models.CharField(max_length=100, blank=True)
    flow_payment_id = models.CharField(max_length=100, blank=True)
    
    # Detalles adicionales
    description = models.CharField(max_length=255, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
    
    def __str__(self):
        return f"Pago {self.payment_id} - {self.user.email} - ${self.amount:,} CLP"
    
    def mark_as_paid(self):
        """Marca el pago como completado"""
        self.status = 'completed'
        self.paid_at = timezone.now()
        self.save()
        
        # Actualizar suscripción
        if self.subscription.is_trial:
            self.subscription.payment_method_added = True
            self.subscription.save()


class Organization(models.Model):
    """Organización para planes empresariales"""
    organization_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    rut = models.CharField(max_length=20, unique=True, help_text="RUT de la empresa")
    
    # Relación con suscripción
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='organization')
    
    # Usuarios de la organización
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_organizations')
    members = models.ManyToManyField(User, related_name='organizations', blank=True)
    
    # Información adicional
    billing_email = models.EmailField()
    billing_address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"
    
    def __str__(self):
        return f"{self.name} ({self.rut})"
    
    @property
    def available_seats(self):
        """Cuántos asientos disponibles quedan"""
        max_users = self.subscription.plan.max_users
        current_users = self.members.count() + 1  # +1 por el owner
        return max(0, max_users - current_users)
    
    def can_add_member(self):
        """Verifica si puede agregar más miembros"""
        return self.available_seats > 0
    
    def add_member(self, user):
        """Agrega un miembro a la organización"""
        if self.can_add_member():
            self.members.add(user)
            return True
        return False