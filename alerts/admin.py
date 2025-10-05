from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import Destinatario, Organizacion, Plan, Subscription, Payment, Organization

class DiasRestantesFilter(admin.SimpleListFilter):
    title = 'Días restantes de trial'
    parameter_name = 'dias_restantes'
    
    def lookups(self, request, model_admin):
        return (
            ('expirado', '❌ Expirado'),
            ('1-3', '⚠️ 1-3 días'),
            ('4-7', '⏰ 4-7 días'),
            ('8-14', '✅ 8-14 días'),
            ('pagado', '💳 Pagado'),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'expirado':
            return queryset.filter(es_pagado=False, fecha_fin_trial__lt=now)
        elif self.value() == '1-3':
            return queryset.filter(
                es_pagado=False,
                fecha_fin_trial__gte=now,
                fecha_fin_trial__lt=now + timedelta(days=3)
            )
        elif self.value() == '4-7':
            return queryset.filter(
                es_pagado=False,
                fecha_fin_trial__gte=now + timedelta(days=3),
                fecha_fin_trial__lt=now + timedelta(days=7)
            )
        elif self.value() == '8-14':
            return queryset.filter(
                es_pagado=False,
                fecha_fin_trial__gte=now + timedelta(days=7)
            )
        elif self.value() == 'pagado':
            return queryset.filter(es_pagado=True)
        return queryset

@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'tipo', 'dominio', 'plan')
    list_filter = ('tipo', 'plan')
    search_fields = ('nombre', 'rut', 'dominio')
    ordering = ('nombre',)

@admin.register(Destinatario)
class DestinatarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'telefono', 'get_organizacion_nombre', 'get_organizacion_rut', 'estado_trial', 'dias_restantes_display', 'fecha_fin_trial')
    list_filter = (DiasRestantesFilter, 'organizacion__tipo', 'organizacion__plan', 'es_pagado')
    search_fields = ('nombre', 'email', 'telefono', 'organizacion__nombre', 'organizacion__rut')
    raw_id_fields = ('organizacion',)
    readonly_fields = ('fecha_inicio_trial', 'fecha_fin_trial', 'estado_trial', 'dias_restantes_display')
    ordering = ('-fecha_fin_trial',)  # Ordenar por fecha de fin de trial, los más próximos primero
    actions = ['extender_trial_7_dias', 'marcar_como_pagado', 'marcar_como_no_pagado']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'email', 'telefono', 'organizacion')
        }),
        ('Período de Prueba', {
            'fields': ('fecha_inicio_trial', 'fecha_fin_trial', 'es_pagado', 'estado_trial', 'dias_restantes_display'),
            'description': 'Información sobre el período de prueba del usuario'
        }),
    )
    
    def get_organizacion_nombre(self, obj):
        return obj.organizacion.nombre if obj.organizacion else '-'
    get_organizacion_nombre.short_description = 'Organización'
    get_organizacion_nombre.admin_order_field = 'organizacion__nombre'
    
    def get_organizacion_rut(self, obj):
        return obj.organizacion.rut if obj.organizacion else '-'
    get_organizacion_rut.short_description = 'RUT Empresa'
    get_organizacion_rut.admin_order_field = 'organizacion__rut'
    
    def estado_trial(self, obj):
        """Muestra el estado del trial con colores"""
        if obj.es_pagado:
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ PAGADO</span>'
            )
        elif obj.trial_activo():
            dias = obj.dias_restantes_trial()
            if dias <= 3:
                color = 'orange'
                emoji = '⚠️'
            elif dias <= 7:
                color = '#FFA500'
                emoji = '⏰'
            else:
                color = 'green'
                emoji = '✅'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} TRIAL ACTIVO</span>',
                color, emoji
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">❌ EXPIRADO</span>'
            )
    estado_trial.short_description = 'Estado'
    
    def dias_restantes_display(self, obj):
        """Muestra los días restantes del trial"""
        if obj.es_pagado:
            return format_html('<span style="color: green;">Sin límite</span>')
        
        dias = obj.dias_restantes_trial()
        if dias > 0:
            if dias == 1:
                texto = f'{dias} día'
            else:
                texto = f'{dias} días'
            
            if dias <= 3:
                color = 'red'
            elif dias <= 7:
                color = 'orange'
            else:
                color = 'green'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, texto
            )
        else:
            return format_html('<span style="color: red;">0 días</span>')
    dias_restantes_display.short_description = 'Días Restantes'
    
    def extender_trial_7_dias(self, request, queryset):
        """Extiende el trial por 7 días más"""
        for obj in queryset:
            if obj.fecha_fin_trial:
                obj.fecha_fin_trial = obj.fecha_fin_trial + timedelta(days=7)
                obj.save()
        self.message_user(request, f'{queryset.count()} usuario(s) extendido(s) por 7 días.')
    extender_trial_7_dias.short_description = '⏰ Extender trial 7 días'
    
    def extender_trial_7_dias(self, request, queryset):
        """Extiende el trial por 7 días más"""
        for obj in queryset:
            if obj.fecha_fin_trial:
                obj.fecha_fin_trial = obj.fecha_fin_trial + timedelta(days=7)
                obj.save()
        self.message_user(request, f'{queryset.count()} usuario(s) extendido(s) por 7 días.')
    extender_trial_7_dias.short_description = '⏰ Extender trial 7 días'
    
    def marcar_como_pagado(self, request, queryset):
        """Marca usuarios como pagados (sin límite de trial)"""
        queryset.update(es_pagado=True)
        self.message_user(request, f'{queryset.count()} usuario(s) marcado(s) como pagado(s).')
    marcar_como_pagado.short_description = '💳 Marcar como pagado'
    
    def marcar_como_no_pagado(self, request, queryset):
        """Marca usuarios como no pagados (sujetos al límite de trial)"""
        queryset.update(es_pagado=False)
        self.message_user(request, f'{queryset.count()} usuario(s) marcado(s) como no pagado(s).')
    marcar_como_no_pagado.short_description = '❌ Marcar como no pagado'


# ==================== ADMIN PARA MODELOS DE SUSCRIPCIÓN ====================

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'formatted_price', 'max_users', 'is_active', 'created_at']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['price']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'slug', 'plan_type', 'description')
        }),
        ('Precios y Límites', {
            'fields': ('price', 'max_users')
        }),
        ('Características', {
            'fields': ('features',),
            'description': 'Características del plan en formato JSON'
        }),
        ('Integración Flow', {
            'fields': ('flow_plan_id',),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def formatted_price(self, obj):
        return format_html('<strong>${:,} CLP</strong>', obj.price)
    formatted_price.short_description = 'Precio'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'plan_name', 'status_badge', 'trial_days_left', 
                   'payment_method_status', 'next_payment', 'created_at']
    list_filter = ['status', 'plan', 'payment_method_added', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'subscription_id']
    readonly_fields = ['subscription_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    fieldsets = (
        ('Información de Usuario', {
            'fields': ('user', 'plan', 'subscription_id')
        }),
        ('Estado de Suscripción', {
            'fields': ('status', 'payment_method_added'),
            'classes': ('wide',)
        }),
        ('Período de Prueba', {
            'fields': ('trial_start', 'trial_end'),
        }),
        ('Período Actual', {
            'fields': ('current_period_start', 'current_period_end', 'next_payment_date'),
        }),
        ('Historial de Pagos', {
            'fields': ('last_payment_date',),
        }),
        ('IDs de Flow', {
            'fields': ('flow_customer_id', 'flow_subscription_id'),
            'classes': ('collapse',),
        }),
        ('Cancelación', {
            'fields': ('canceled_at',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    actions = ['marcar_como_activa', 'marcar_como_cancelada', 'exportar_csv']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Usuario'
    
    def plan_name(self, obj):
        return obj.plan.name
    plan_name.short_description = 'Plan'
    
    def status_badge(self, obj):
        colors = {
            'trial': '#fbbf24',
            'active': '#10b981',
            'past_due': '#f97316',
            'canceled': '#ef4444',
            'expired': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def trial_days_left(self, obj):
        if obj.is_trial:
            days = obj.days_until_trial_end
            if days > 7:
                color = 'green'
            elif days > 3:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{} días</span>',
                color, days
            )
        return '-'
    trial_days_left.short_description = 'Trial restante'
    
    def payment_method_status(self, obj):
        if obj.payment_method_added:
            return format_html('<span style="color: green;">✅ Agregado</span>')
        elif obj.is_trial:
            return format_html('<span style="color: orange;">⚠️ Pendiente</span>')
        return '-'
    payment_method_status.short_description = 'Método de pago'
    
    def next_payment(self, obj):
        if obj.next_payment_date:
            return obj.next_payment_date.strftime('%d/%m/%Y')
        return '-'
    next_payment.short_description = 'Próximo pago'
    
    def marcar_como_activa(self, request, queryset):
        """Marca suscripciones como activas"""
        queryset.update(status='active')
        self.message_user(request, f'{queryset.count()} suscripción(es) marcada(s) como activa(s).')
    marcar_como_activa.short_description = '✅ Marcar como activa'
    
    def marcar_como_cancelada(self, request, queryset):
        """Marca suscripciones como canceladas"""
        for sub in queryset:
            sub.cancel()
        self.message_user(request, f'{queryset.count()} suscripción(es) cancelada(s).')
    marcar_como_cancelada.short_description = '❌ Cancelar suscripción'
    
    def exportar_csv(self, request, queryset):
        """Exporta suscripciones a CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="suscripciones.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Plan', 'Estado', 'Fecha Inicio', 'Próximo Pago', 'Método Pago'])
        
        for obj in queryset:
            writer.writerow([
                obj.user.email,
                obj.plan.name,
                obj.get_status_display(),
                obj.created_at.strftime('%d/%m/%Y'),
                obj.next_payment_date.strftime('%d/%m/%Y') if obj.next_payment_date else '-',
                'Sí' if obj.payment_method_added else 'No'
            ])
        
        return response
    exportar_csv.short_description = '📥 Exportar a CSV'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id_short', 'user_email', 'amount_formatted', 
                   'status_badge', 'payment_method', 'created_at', 'paid_at']
    list_filter = ['status', 'plan', 'payment_method', 'created_at']
    search_fields = ['user__email', 'payment_id', 'flow_order_id', 'flow_token']
    readonly_fields = ['payment_id', 'created_at', 'paid_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('payment_id', 'user', 'subscription', 'plan')
        }),
        ('Detalles del Pago', {
            'fields': ('amount', 'status', 'payment_method', 'description'),
            'classes': ('wide',)
        }),
        ('IDs de Flow', {
            'fields': ('flow_order_id', 'flow_token', 'flow_payment_id'),
            'classes': ('collapse',)
        }),
        ('Resultado', {
            'fields': ('failure_reason', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'paid_at'),
        }),
    )
    
    actions = ['marcar_como_pagado', 'marcar_como_fallido', 'exportar_pagos_csv']
    
    def payment_id_short(self, obj):
        return str(obj.payment_id)[:8] + '...'
    payment_id_short.short_description = 'ID Pago'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Usuario'
    
    def amount_formatted(self, obj):
        return format_html('${:,} CLP', obj.amount)
    amount_formatted.short_description = 'Monto'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#fbbf24',
            'processing': '#3b82f6',
            'completed': '#10b981',
            'failed': '#ef4444',
            'refunded': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def marcar_como_pagado(self, request, queryset):
        """Marca pagos como completados"""
        for payment in queryset:
            payment.mark_as_paid()
        self.message_user(request, f'{queryset.count()} pago(s) marcado(s) como completado(s).')
    marcar_como_pagado.short_description = '✅ Marcar como pagado'
    
    def marcar_como_fallido(self, request, queryset):
        """Marca pagos como fallidos"""
        queryset.update(status='failed')
        self.message_user(request, f'{queryset.count()} pago(s) marcado(s) como fallido(s).')
    marcar_como_fallido.short_description = '❌ Marcar como fallido'
    
    def exportar_pagos_csv(self, request, queryset):
        """Exporta pagos a CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pagos.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Usuario', 'Monto', 'Estado', 'Método', 'Fecha Creación', 'Fecha Pago'])
        
        for obj in queryset:
            writer.writerow([
                str(obj.payment_id)[:8],
                obj.user.email,
                obj.amount,
                obj.get_status_display(),
                obj.payment_method or '-',
                obj.created_at.strftime('%d/%m/%Y %H:%M'),
                obj.paid_at.strftime('%d/%m/%Y %H:%M') if obj.paid_at else '-'
            ])
        
        return response
    exportar_pagos_csv.short_description = '📥 Exportar pagos a CSV'


@admin.register(Organization)
class OrganizationAdminNew(admin.ModelAdmin):
    list_display = ['name', 'rut', 'owner_email', 'members_count', 'seats_available']
    list_filter = ['created_at']
    search_fields = ['name', 'rut', 'owner__email', 'billing_email']
    readonly_fields = ['organization_id', 'created_at', 'updated_at']
    filter_horizontal = ['members']
    
    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Propietario'
    
    def members_count(self, obj):
        count = obj.members.count() + 1  # +1 por el owner
        max_users = obj.subscription.plan.max_users
        return format_html('{} / {}', count, max_users)
    members_count.short_description = 'Miembros'
    
    def seats_available(self, obj):
        available = obj.available_seats
        if available > 0:
            return format_html(
                '<span style="color: green;">{} disponibles</span>',
                available
            )
        return format_html(
            '<span style="color: red;">Sin cupos</span>'
        )
    seats_available.short_description = 'Cupos'
