from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import Destinatario, Organizacion

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
    actions = ['extender_trial_7_dias', 'extender_trial_14_dias', 'marcar_como_pagado', 'marcar_como_no_pagado']
    
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
    
    def extender_trial_14_dias(self, request, queryset):
        """Extiende el trial por 14 días más"""
        for obj in queryset:
            if obj.fecha_fin_trial:
                obj.fecha_fin_trial = obj.fecha_fin_trial + timedelta(days=14)
                obj.save()
        self.message_user(request, f'{queryset.count()} usuario(s) extendido(s) por 14 días.')
    extender_trial_14_dias.short_description = '⏰ Extender trial 14 días'
    
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
