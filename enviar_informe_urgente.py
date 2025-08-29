#!/usr/bin/env python3
"""
Script urgente para enviar el informe de hoy
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')

import django
django.setup()

# Importar después de configurar Django
from django.core.management import call_command

print(f"\n🚀 ENVIANDO INFORME DIARIO - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)

try:
    # Ejecutar el comando de Django directamente
    call_command('enviar_informes_diarios')
    print("\n✅ Comando ejecutado exitosamente")
    
except KeyboardInterrupt:
    print("\n⚠️ Proceso interrumpido por el usuario")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    
    # Intentar método alternativo
    print("\n🔄 Intentando método alternativo...")
    
    try:
        # Importar las funciones necesarias
        from generar_informe_oficial_integrado_mejorado import main as generar_informe_main
        
        # Generar y enviar informe
        generar_informe_main()
        print("✅ Informe enviado por método alternativo")
        
    except Exception as e2:
        print(f"❌ Error en método alternativo: {str(e2)}")
        
        # Último intento
        print("\n🔄 Último intento...")
        os.system("python generar_informe_oficial_integrado_mejorado.py")

print("\n" + "=" * 60)
print("Proceso completado")