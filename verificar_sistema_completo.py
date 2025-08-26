#!/usr/bin/env python
"""
Script para verificar que todo esté listo para el envío del informe mañana
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.models import Destinatario, Organizacion
from django.contrib.auth.models import User

print("\n" + "="*70)
print("VERIFICACIÓN COMPLETA DEL SISTEMA PARA ENVÍO DE INFORMES")
print("="*70 + "\n")

# 1. Verificar destinatarios y trials
print("📊 1. VERIFICANDO DESTINATARIOS Y PERÍODOS DE PRUEBA")
print("-" * 50)

destinatarios = Destinatario.objects.all()
print(f"Total de destinatarios: {destinatarios.count()}")

activos = []
expirados = []

for dest in destinatarios:
    if dest.trial_activo():
        activos.append(dest)
        dias = dest.dias_restantes_trial()
        print(f"  ✅ {dest.email:40} - {dias} días restantes")
    else:
        expirados.append(dest)
        print(f"  ❌ {dest.email:40} - EXPIRADO")

print(f"\nResumen:")
print(f"  • Recibirán informe mañana: {len(activos)} usuarios")
print(f"  • NO recibirán (expirados): {len(expirados)} usuarios")

# 2. Verificar configuración de email
print("\n📧 2. VERIFICANDO CONFIGURACIÓN DE EMAIL")
print("-" * 50)

from django.conf import settings
email_config = {
    'HOST': os.environ.get('SMTP_HOST', 'No configurado'),
    'PORT': os.environ.get('SMTP_PORT', 'No configurado'),
    'USER': os.environ.get('SMTP_USER', 'No configurado'),
    'PASSWORD': '***CONFIGURADO***' if os.environ.get('HOSTINGER_EMAIL_PASSWORD') else '❌ NO CONFIGURADO'
}

for key, value in email_config.items():
    status = "✅" if value != 'No configurado' else "❌"
    print(f"  {status} {key}: {value}")

# 3. Verificar horario de envío
print("\n⏰ 3. VERIFICANDO HORARIO DE ENVÍO")
print("-" * 50)

ahora = datetime.now()
manana_9am = ahora.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
horas_restantes = (manana_9am - ahora).total_seconds() / 3600

print(f"  Hora actual: {ahora.strftime('%H:%M:%S')}")
print(f"  Próximo envío: {manana_9am.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Faltan: {horas_restantes:.1f} horas")

# 4. Lista de emails que recibirán el informe
print("\n📬 4. EMAILS QUE RECIBIRÁN EL INFORME MAÑANA:")
print("-" * 50)

if activos:
    for i, dest in enumerate(activos, 1):
        print(f"  {i:2}. {dest.email}")
else:
    print("  ⚠️  No hay destinatarios activos")

print("\n" + "="*70)
print("RESUMEN FINAL:")
print("="*70)

todo_ok = True
mensajes = []

if len(activos) > 0:
    mensajes.append(f"✅ {len(activos)} usuarios recibirán el informe")
else:
    mensajes.append("❌ No hay usuarios activos para recibir informes")
    todo_ok = False

if email_config['PASSWORD'] == '***CONFIGURADO***':
    mensajes.append("✅ Configuración de email correcta")
else:
    mensajes.append("❌ Falta configuración de email")
    todo_ok = False

for msg in mensajes:
    print(f"  {msg}")

if todo_ok:
    print("\n🎉 TODO ESTÁ LISTO PARA EL ENVÍO DE MAÑANA A LAS 9:00 AM")
else:
    print("\n⚠️  HAY PROBLEMAS QUE RESOLVER ANTES DEL ENVÍO")
