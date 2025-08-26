#!/usr/bin/env python
"""
Script para listar usuarios en producción y asignarles trial de 14 días
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Destinatario, Organizacion

print("\n" + "="*60)
print("USUARIOS EN PRODUCCIÓN")
print("="*60 + "\n")

# Listar usuarios
usuarios = User.objects.all()
print(f"📊 Total de usuarios Django: {usuarios.count()}")
for user in usuarios[:10]:  # Mostrar solo los primeros 10
    print(f"  • {user.username} - {user.email}")
if usuarios.count() > 10:
    print(f"  ... y {usuarios.count() - 10} más")

print("\n" + "-" * 40)

# Listar destinatarios
destinatarios = Destinatario.objects.all()
print(f"\n📊 Total de destinatarios: {destinatarios.count()}")

# Establecer fecha de trial para todos los que no la tengan
ahora = timezone.now()
fecha_fin = ahora + timedelta(days=14)
actualizados = 0

for dest in destinatarios:
    if not dest.fecha_inicio_trial or not dest.fecha_fin_trial:
        dest.fecha_inicio_trial = ahora
        dest.fecha_fin_trial = fecha_fin
        dest.es_pagado = False
        dest.save()
        actualizados += 1
        print(f"✅ {dest.email} - Trial activado hasta {fecha_fin.date()}")
    else:
        dias = dest.dias_restantes_trial()
        estado = "✅ Activo" if dest.trial_activo() else "❌ Expirado"
        print(f"  • {dest.email} - {estado} ({dias} días restantes)")

if actualizados > 0:
    print(f"\n✅ Se activó el trial para {actualizados} usuarios")

print("\n" + "="*60)