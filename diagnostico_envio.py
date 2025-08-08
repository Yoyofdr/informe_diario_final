#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.models import Destinatario, InformeDiarioCache
from datetime import datetime, date

# Verificar destinatarios
print("=" * 50)
print("DIAGNÓSTICO DE ENVÍO DE INFORMES")
print("=" * 50)

# 1. Verificar destinatarios
print("\n1. DESTINATARIOS REGISTRADOS:")
destinatarios = Destinatario.objects.all()
print(f"Total destinatarios: {destinatarios.count()}")
print("\nLista de destinatarios:")
for dest in destinatarios:
    org_nombre = dest.organizacion.nombre if dest.organizacion else "Sin organización"
    print(f"  - {dest.email} ({dest.nombre} - {org_nombre})")

# 2. Verificar informes en caché
print("\n2. INFORMES EN CACHÉ:")
hoy = date.today()
ayer = date(2025, 8, 7)  # Ayer
informe_hoy = InformeDiarioCache.objects.filter(fecha=hoy).first()
informe_ayer = InformeDiarioCache.objects.filter(fecha=ayer).first()

print(f"Informe de hoy ({hoy}): {'SÍ' if informe_hoy else 'NO'} existe en caché")
print(f"Informe de ayer ({ayer}): {'SÍ' if informe_ayer else 'NO'} existe en caché")

# 3. Verificar configuración de email
print("\n3. CONFIGURACIÓN DE EMAIL:")
print(f"EMAIL_HOST_USER: {os.getenv('EMAIL_HOST_USER', 'NO CONFIGURADO')}")
print(f"SMTP_SERVER: {os.getenv('SMTP_SERVER', 'smtp.hostinger.com')}")
print(f"SMTP_PORT: {os.getenv('SMTP_PORT', '587')}")
print(f"HOSTINGER_EMAIL_PASSWORD: {'CONFIGURADO' if os.getenv('HOSTINGER_EMAIL_PASSWORD') else 'NO CONFIGURADO'}")

# 4. Test de envío manual
print("\n4. TEST DE ENVÍO:")
print("Para hacer un test de envío, ejecuta:")
print("python scripts/generators/generar_informe_oficial_integrado_mejorado.py")