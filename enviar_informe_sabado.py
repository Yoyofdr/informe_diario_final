#!/usr/bin/env python3
"""
Script de emergencia para enviar el informe del sábado
"""
import os
import sys
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')

import django
django.setup()

from datetime import datetime

print(f"\n🚀 ENVIANDO INFORME DEL SÁBADO - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)

# Verificar que no es domingo
if datetime.now().weekday() == 6:
    print("❌ Es domingo - No se envían informes")
    sys.exit(0)

print(f"✅ Hoy es sábado - Procediendo con el envío...")

try:
    # Importar después de configurar Django
    from django.core.management import call_command
    
    # Ejecutar el comando
    call_command('enviar_informes_diarios')
    print("\n✅ Informe enviado exitosamente")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    print("\n🔄 Intentando método alternativo directo...")
    
    # Método alternativo - llamar al script directamente
    try:
        from scripts.generators import generar_informe_oficial_integrado_mejorado
        fecha_hoy = datetime.now().strftime("%d-%m-%Y")
        resultado = generar_informe_oficial_integrado_mejorado.generar_informe_oficial(fecha=fecha_hoy)
        if resultado:
            print("✅ Informe enviado por método alternativo")
        else:
            print("❌ No se pudo enviar el informe")
    except Exception as e2:
        print(f"❌ Error en método alternativo: {str(e2)}")

print("\n" + "=" * 60)
print("Proceso completado")