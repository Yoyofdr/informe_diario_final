from django.contrib import admin
from .models import Destinatario, Organizacion

@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'tipo', 'dominio', 'fecha_creacion')
    list_filter = ('tipo', 'plan', 'fecha_creacion')
    search_fields = ('nombre', 'rut', 'dominio')
    readonly_fields = ('fecha_creacion',)
    ordering = ('-fecha_creacion',)

@admin.register(Destinatario)
class DestinatarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'telefono', 'get_organizacion_nombre', 'get_organizacion_rut')
    list_filter = ('organizacion__tipo', 'organizacion__plan')
    search_fields = ('nombre', 'email', 'telefono', 'organizacion__nombre', 'organizacion__rut')
    raw_id_fields = ('organizacion',)
    
    def get_organizacion_nombre(self, obj):
        return obj.organizacion.nombre if obj.organizacion else '-'
    get_organizacion_nombre.short_description = 'Organización'
    get_organizacion_nombre.admin_order_field = 'organizacion__nombre'
    
    def get_organizacion_rut(self, obj):
        return obj.organizacion.rut if obj.organizacion else '-'
    get_organizacion_rut.short_description = 'RUT Empresa'
    get_organizacion_rut.admin_order_field = 'organizacion__rut'
