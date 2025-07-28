from django.contrib import admin
from .models import Destinatario

@admin.register(Destinatario)
class DestinatarioAdmin(admin.ModelAdmin):
    list_display = ('email',)
    search_fields = ('email',)
