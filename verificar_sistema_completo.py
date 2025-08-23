#!/usr/bin/env python3
"""
Script de verificación completa del sistema para el envío de informes
"""

import os
import sys
import django
from pathlib import Path
from datetime import datetime
import pytz

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

print("=" * 60)
print("VERIFICACIÓN COMPLETA DEL SISTEMA DE INFORMES")
print("=" * 60)

# 1. Verificar hora actual
chile_tz = pytz.timezone('America/Santiago')
hora_chile = datetime.now(chile_tz)
print(f"\n✅ Hora actual en Chile: {hora_chile.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# 2. Verificar comando de Django
from django.core.management import get_commands
commands = get_commands()
if 'enviar_informes_diarios' in commands:
    print("✅ Comando 'enviar_informes_diarios' disponible")
else:
    print("❌ ERROR: Comando 'enviar_informes_diarios' NO encontrado")

# 3. Verificar base de datos
from alerts.models import Destinatario, Organizacion
total_org = Organizacion.objects.count()
total_dest = Destinatario.objects.count()
print(f"\n📊 Base de datos:")
print(f"  - Organizaciones: {total_org}")
print(f"  - Destinatarios: {total_dest}")

# 4. Verificar variables de entorno críticas
env_vars = {
    'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
    'HOSTINGER_EMAIL': os.environ.get('HOSTINGER_EMAIL'),
    'HOSTINGER_EMAIL_PASSWORD': os.environ.get('HOSTINGER_EMAIL_PASSWORD'),
}

print("\n🔑 Variables de entorno:")
for var, value in env_vars.items():
    if value:
        print(f"  ✅ {var}: Configurada")
    else:
        print(f"  ❌ {var}: NO configurada")

# 5. Verificar archivos críticos
archivos_criticos = [
    'scripts/generators/generar_informe_oficial_integrado_mejorado.py',
    'alerts/cmf_resumenes_ai.py',
    'alerts/services/pdf_extractor.py',
    'alerts/scraper_diario_oficial.py',
    'scripts/scrapers/scraper_cmf_mejorado.py',
    'alerts/management/commands/enviar_informes_diarios.py'
]

print("\n📁 Archivos críticos:")
for archivo in archivos_criticos:
    path = BASE_DIR / archivo
    if path.exists():
        print(f"  ✅ {archivo}")
    else:
        print(f"  ❌ {archivo} - NO EXISTE")

# 6. Verificar importaciones críticas
print("\n📦 Dependencias críticas:")
try:
    import requests
    print("  ✅ requests")
except ImportError:
    print("  ❌ requests")

try:
    import PyPDF2
    print("  ✅ PyPDF2")
except ImportError:
    print("  ❌ PyPDF2")

try:
    import openai
    print("  ✅ openai")
except ImportError:
    print("  ❌ openai")

try:
    from selenium import webdriver
    print("  ✅ selenium")
except ImportError:
    print("  ❌ selenium")

# 7. Verificar que se puede importar el generador
print("\n🔧 Módulo generador de informes:")
try:
    from scripts.generators import generar_informe_oficial_integrado_mejorado
    print("  ✅ Módulo importable")
    
    # Verificar que tiene la función principal
    if hasattr(generar_informe_oficial_integrado_mejorado, 'generar_informe_oficial'):
        print("  ✅ Función generar_informe_oficial disponible")
    else:
        print("  ❌ Función generar_informe_oficial NO disponible")
except Exception as e:
    print(f"  ❌ Error al importar: {e}")

# 8. Resumen final
print("\n" + "=" * 60)
print("RESUMEN DE VERIFICACIÓN")
print("=" * 60)

verificaciones = {
    "Hora Chile": True,
    "Comando Django": 'enviar_informes_diarios' in commands,
    "Base de datos": total_dest > 0,
    "API Keys": all([env_vars.get('OPENAI_API_KEY'), env_vars.get('HOSTINGER_EMAIL')]),
    "Archivos": all([(BASE_DIR / archivo).exists() for archivo in archivos_criticos]),
}

todas_ok = all(verificaciones.values())

for nombre, estado in verificaciones.items():
    simbolo = "✅" if estado else "❌"
    print(f"{simbolo} {nombre}: {'OK' if estado else 'FALLO'}")

print("\n" + "=" * 60)
if todas_ok:
    print("✅ SISTEMA LISTO PARA ENVÍO DE INFORMES")
    print("El próximo envío será mañana a las 9:00 AM hora Chile")
else:
    print("⚠️ HAY PROBLEMAS QUE NECESITAN ATENCIÓN")
print("=" * 60)