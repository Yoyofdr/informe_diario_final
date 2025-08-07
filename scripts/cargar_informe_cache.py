#!/usr/bin/env python3
"""
Script para cargar el informe de hoy en el caché de la base de datos
"""
import os
import sys
import django
from datetime import datetime
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.utils.cache_informe import CacheInformeDiario

def cargar_informe_existente():
    """Carga el informe HTML del 06-08-2025 en el caché"""
    
    # Buscar el archivo HTML
    archivo_informe = BASE_DIR / "informe_diario_06_08_2025.html"
    
    if not archivo_informe.exists():
        print(f"❌ No se encontró el archivo: {archivo_informe}")
        return False
    
    try:
        # Leer el contenido HTML
        with open(archivo_informe, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"✅ Archivo leído: {len(html_content)} caracteres")
        
        # Guardar en caché
        cache = CacheInformeDiario()
        fecha = datetime(2025, 8, 6).date()  # 6 de agosto de 2025
        
        if cache.guardar_informe(html_content, fecha):
            print(f"✅ Informe guardado en caché para fecha: {fecha}")
            
            # Verificar que se guardó correctamente
            html_recuperado = cache.obtener_informe(fecha)
            if html_recuperado:
                print(f"✅ Verificación exitosa: informe recuperado del caché ({len(html_recuperado)} caracteres)")
                return True
            else:
                print("❌ Error: No se pudo recuperar el informe del caché")
                return False
        else:
            print("❌ Error guardando informe en caché")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    cargar_informe_existente()