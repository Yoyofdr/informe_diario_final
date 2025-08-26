from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .validators import validar_rut_estricto

class PerfilUsuario(models.Model):
    """
    Extiende el modelo de usuario para añadir el plan de suscripción.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    suscripciones = models.ManyToManyField('Empresa', blank=True, related_name='perfiles_suscritos')

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def crear_o_actualizar_perfil_usuario(sender, instance, created, **kwargs):
    """
    Asegura que cada usuario tenga un perfil.
    """
    if created:
        PerfilUsuario.objects.create(user=instance)
    
    # Esto puede ser redundante si el perfil se crea y guarda, pero asegura que exista.
    if not hasattr(instance, 'perfil'):
         PerfilUsuario.objects.create(user=instance)
    instance.perfil.save()

class Empresa(models.Model):
    """
    Representa una empresa emisora de Hechos Esenciales.
    """
    nombre = models.CharField(max_length=255, unique=True)
    rut = models.CharField(max_length=20, blank=True, null=True, unique=True)
    rubro = models.CharField(max_length=100, blank=True, null=True, help_text="Rubro o industria de la empresa.")
    es_ipsa = models.BooleanField(default=False, help_text="Indica si la empresa forma parte del índice IPSA.")
    notificacion_enviada = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nombre']

class HechoEsencial(models.Model):
    """
    Representa un Hecho Esencial publicado por una empresa.
    """
    RELEVANCIA_CHOICES = [
        (1, 'Baja'),
        (2, 'Media'),
        (3, 'Alta'),
    ]
    
    CATEGORIA_CHOICES = [
        ('CRITICO', 'Crítico'),
        ('IMPORTANTE', 'Importante'),
        ('MODERADO', 'Moderado'),
        ('RUTINARIO', 'Rutinario'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='hechos_esenciales')
    titulo = models.CharField(max_length=500)
    url = models.URLField(max_length=500, unique=True)
    fecha_publicacion = models.DateTimeField()
    resumen = models.TextField(blank=True, null=True, help_text="Resumen del hecho esencial generado por IA.")
    relevancia = models.IntegerField(choices=RELEVANCIA_CHOICES, blank=True, null=True, help_text="Nivel de relevancia determinado por IA.")
    notificacion_enviada = models.BooleanField(default=False)
    
    # Nuevos campos para criterios profesionales
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='MODERADO', help_text="Categoría según criterios profesionales")
    relevancia_profesional = models.FloatField(default=5.0, help_text="Relevancia profesional (1-10)")
    es_empresa_ipsa = models.BooleanField(default=False, help_text="Indica si la empresa es parte del IPSA al momento del hecho")
    materia = models.CharField(max_length=500, blank=True, null=True, help_text="Contexto adicional del hecho")

    class Meta:
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f"{self.empresa.nombre} - {self.fecha_publicacion}"

class Alerta(models.Model):
    """
    Representa un Hecho Esencial publicado por una empresa.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='alertas')
    fecha_publicacion = models.DateTimeField()
    numero_documento = models.CharField(max_length=50, unique=True)
    url_documento = models.URLField(max_length=500)
    contenido = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Alerta de {self.empresa.nombre} - {self.numero_documento}"

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-fecha_publicacion']

class Suscripcion(models.Model):
    """
    DEPRECATED: Este modelo ha sido reemplazado por la relación ManyToMany en PerfilUsuario.
    Se mantiene temporalmente para evitar errores de migración, pero no se utiliza en la lógica nueva.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    activa = models.BooleanField(default=True)

    class Meta:
        # unique_together = ('usuario', 'empresa') # Comentado para evitar conflictos
        pass

class NotificacionEnviada(models.Model):
    """
    Registra cada notificación de Hecho Esencial que se ha enviado a un usuario.
    Esto es crucial para respetar los límites del plan de suscripción.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    hecho_esencial = models.ForeignKey(HechoEsencial, on_delete=models.CASCADE)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'hecho_esencial')

    def __str__(self):
        return f"Notificación para {self.usuario.username} sobre {self.hecho_esencial.empresa.nombre} el {self.fecha_envio.strftime('%Y-%m-%d')}"

class Organizacion(models.Model):
    # Choices para tipo de organización
    class Tipo(models.TextChoices):
        EMPRESA = "empresa", "Empresa"
        INDEPENDIENTE = "independiente", "Independiente"
    
    nombre = models.CharField(max_length=200)
    dominio = models.CharField(max_length=80, null=True, blank=True, help_text="Campo legacy - no se usa para agrupar")
    fecha_pago = models.DateTimeField(null=True, blank=True)
    suscripcion_activa = models.BooleanField(default=False)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organizaciones')
    
    # Nuevos campos para sistema basado en RUT
    rut = models.CharField(
        max_length=11, 
        unique=True, 
        null=True, 
        blank=True,
        validators=[validar_rut_estricto],
        help_text="RUT en formato NNNNNNNN-DV (sin puntos, DV mayúscula)"
    )
    tipo = models.CharField(
        max_length=20, 
        choices=Tipo.choices, 
        default=Tipo.INDEPENDIENTE,
        help_text="Tipo de organización: Empresa (con RUT) o Independiente"
    )
    
    # Campos para futura integración bancaria - NO USAR AÚN
    # Estos campos están preparados para cuando se active la funcionalidad de cuentas bancarias
    bank_account_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pendiente'),
            ('connected', 'Conectada'),
            ('failed', 'Falló'),
            ('disconnected', 'Desconectada')
        ],
        default='pending',
        help_text='CAMPO RESERVADO - No usar hasta activar funcionalidad bancaria'
    )
    
    PLAN_CHOICES = [
        ('gratis', 'Gratis'),
        ('premium', 'Premium'),
    ]
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='gratis')

    def __str__(self):
        return f"{self.nombre} ({self.dominio})"

class Destinatario(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True, null=True)
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name='destinatarios')
    
    # Campos para trial de 2 semanas
    fecha_inicio_trial = models.DateTimeField(default=timezone.now, help_text="Fecha de inicio del período de prueba")
    es_pagado = models.BooleanField(default=False, help_text="Indica si el cliente tiene una suscripción pagada activa")
    fecha_fin_trial = models.DateTimeField(null=True, blank=True, help_text="Fecha de fin del período de prueba (se calcula automáticamente)")
    
    def save(self, *args, **kwargs):
        # Calcular fecha de fin de trial si es nuevo registro
        if not self.pk and not self.fecha_fin_trial:
            self.fecha_fin_trial = self.fecha_inicio_trial + timedelta(days=14)
        super().save(*args, **kwargs)
    
    def trial_activo(self):
        """Verifica si el trial está activo"""
        # Por ahora, solo verificamos si está dentro del período de 14 días
        if not self.fecha_fin_trial:
            return False
        return timezone.now() <= self.fecha_fin_trial
    
    def dias_restantes_trial(self):
        """Retorna los días restantes del trial"""
        if not self.fecha_fin_trial:
            return 0
        dias = (self.fecha_fin_trial - timezone.now()).days
        return max(0, dias)

    def __str__(self):
        return f"{self.nombre} <{self.email}>"

class RegistroPago(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=30, choices=[('pendiente', 'Pendiente'), ('pagado', 'Pagado'), ('fallido', 'Fallido')], default='pendiente')

    def __str__(self):
        return f"Pago {self.monto} - {self.organizacion.nombre} ({self.estado})"

class SuscripcionLanding(models.Model):
    email = models.EmailField()
    organizacion = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.email} ({self.organizacion})"

class InformeEnviado(models.Model):
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    destinatarios = models.TextField()
    enlace_html = models.CharField(max_length=255, blank=True, null=True)
    resumen = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Informe {self.empresa.nombre} - {self.fecha_envio.date()}"

class DocumentoSII(models.Model):
    """
    Representa un documento del Servicio de Impuestos Internos (circulares, resoluciones, jurisprudencia)
    """
    TIPO_DOCUMENTO_CHOICES = [
        ('CIRCULAR', 'Circular'),
        ('RESOLUCION', 'Resolución'),
        ('JURISPRUDENCIA', 'Jurisprudencia'),
    ]
    
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    numero = models.CharField(max_length=50)
    titulo = models.CharField(max_length=500)
    url = models.URLField(max_length=500)
    fecha_publicacion = models.DateField()
    contenido = models.TextField(blank=True, null=True)
    resumen = models.TextField(blank=True, null=True, help_text="Resumen generado por IA")
    relevancia = models.IntegerField(default=2, help_text="Relevancia (1-3)")
    es_relevante = models.BooleanField(default=True, help_text="Si debe incluirse en informes")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_publicacion']
        unique_together = ('tipo_documento', 'numero')
        
    def __str__(self):
        return f"{self.get_tipo_documento_display()} {self.numero} - {self.titulo}"


class InformeDiarioCache(models.Model):
    """
    Caché del informe diario generado para evitar regenerarlo
    """
    fecha = models.DateField(unique=True)
    html_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata opcional
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Informe del {self.fecha}"
    
    class Meta:
        db_table = 'alerts_informediariocache'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['fecha']),
        ]
    
    @classmethod
    def get_or_none(cls, fecha):
        """Obtiene el informe de una fecha o None si no existe"""
        try:
            return cls.objects.get(fecha=fecha)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def save_report(cls, fecha, html_content, metadata=None):
        """Guarda o actualiza el informe de una fecha"""
        informe, created = cls.objects.update_or_create(
            fecha=fecha,
            defaults={
                'html_content': html_content,
                'metadata': metadata or {}
            }
        )
        return informe
