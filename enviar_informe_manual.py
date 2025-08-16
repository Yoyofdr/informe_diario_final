#!/usr/bin/env python3
"""
Script para enviar el informe manualmente
"""
import os
import sys
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
import django
django.setup()

from django.core.management import call_command

print("🚀 Enviando informe manual...")
print(f"Fecha/hora: {datetime.now()}")

try:
    # Ejecutar el comando de envío
    call_command('enviar_informes_diarios')
    print("✅ Informe enviado exitosamente")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()