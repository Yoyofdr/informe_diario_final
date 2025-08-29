#!/usr/bin/env python3
"""
Verificación exhaustiva de scrapers ambientales
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

print("🔍 VERIFICACIÓN COMPLETA DE SCRAPERS AMBIENTALES")
print("=" * 80)

# 1. PROBAR SCRAPER SEA FINAL
print("\n1️⃣ PROBANDO SCRAPER SEA FINAL (Selenium)")
print("-" * 40)

try:
    from scripts.scrapers.scraper_sea_final import ScraperSEAFinal
    scraper_sea = ScraperSEAFinal()
    proyectos_sea = scraper_sea.obtener_datos_sea(dias_atras=7)
    
    print(f"✅ Scraper SEA Final funcionando")
    print(f"   Proyectos encontrados: {len(proyectos_sea)}")
    
    if proyectos_sea:
        print("\n   Primeros 3 proyectos:")
        for i, p in enumerate(proyectos_sea[:3], 1):
            print(f"   {i}. {p.get('titulo', 'Sin título')[:60]}...")
            print(f"      Fecha: {p.get('fecha_presentacion', 'N/A')}")
            print(f"      Tipo: {p.get('tipo', 'N/A')}")
    else:
        print("   ⚠️ No se encontraron proyectos")
        
except Exception as e:
    print(f"❌ Error en Scraper SEA Final: {str(e)}")
    proyectos_sea = []

# 2. PROBAR SCRAPER SMA/SNIFA
print("\n2️⃣ PROBANDO SCRAPER SMA/SNIFA")
print("-" * 40)

try:
    from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
    scraper_sma = ScraperSNIFAWeb()
    sanciones_sma = scraper_sma.obtener_sanciones_recientes(dias_atras=7)
    
    print(f"✅ Scraper SMA/SNIFA funcionando")
    print(f"   Sanciones encontradas: {len(sanciones_sma)}")
    
    if sanciones_sma:
        print("\n   Primeras 3 sanciones:")
        for i, s in enumerate(sanciones_sma[:3], 1):
            print(f"   {i}. Expediente: {s.get('expediente', 'N/A')}")
            print(f"      Empresa: {s.get('empresa', 'N/A')}")
            print(f"      Multa: {s.get('multa_formato', 'N/A')}")
    else:
        print("   ⚠️ No se encontraron sanciones recientes")
        
except Exception as e:
    print(f"❌ Error en Scraper SMA/SNIFA: {str(e)}")
    sanciones_sma = []

# 3. PROBAR SCRAPER INTEGRADO
print("\n3️⃣ PROBANDO SCRAPER AMBIENTAL INTEGRADO")
print("-" * 40)

try:
    from scripts.scrapers.scraper_ambiental_integrado import ScraperAmbiental
    scraper_integrado = ScraperAmbiental()
    datos_ambientales = scraper_integrado.obtener_datos_ambientales(dias_atras=7)
    
    proyectos_int = datos_ambientales.get('proyectos_sea', [])
    sanciones_int = datos_ambientales.get('sanciones_sma', [])
    
    print(f"✅ Scraper Integrado funcionando")
    print(f"   Proyectos SEA: {len(proyectos_int)}")
    print(f"   Sanciones SMA: {len(sanciones_int)}")
    print(f"   Total elementos: {len(proyectos_int) + len(sanciones_int)}")
    
except Exception as e:
    print(f"❌ Error en Scraper Integrado: {str(e)}")

# 4. DIAGNÓSTICO FINAL
print("\n" + "=" * 80)
print("📊 DIAGNÓSTICO FINAL")
print("-" * 40)

total_datos = len(proyectos_sea) + len(sanciones_sma)

if total_datos > 0:
    print(f"✅ SCRAPERS FUNCIONANDO CORRECTAMENTE")
    print(f"   Total datos ambientales disponibles: {total_datos}")
    
    if len(proyectos_sea) == 0:
        print("\n⚠️ ADVERTENCIA: Scraper SEA no está obteniendo datos")
        print("   Posibles causas:")
        print("   - El sitio SEIA puede estar bloqueando requests")
        print("   - No hay proyectos nuevos en los últimos días")
        print("   - Se necesita ajustar los selectores HTML")
        
    if len(sanciones_sma) == 0:
        print("\n⚠️ ADVERTENCIA: Scraper SMA no está obteniendo datos")
        print("   Posibles causas:")
        print("   - No hay sanciones recientes publicadas")
        print("   - La estructura del sitio SNIFA cambió")
        
else:
    print(f"❌ PROBLEMA CRÍTICO: Ningún scraper está obteniendo datos")
    print("\nACCIONES RECOMENDADAS:")
    print("1. Verificar conexión a internet")
    print("2. Revisar si los sitios web están disponibles")
    print("3. Actualizar selectores HTML si cambió la estructura")
    print("4. Considerar usar proxies o rotar user agents")

print("\n" + "=" * 80)

# 5. VERIFICAR PROYECTOS ESPECÍFICOS DEL 26/08
print("\n🔍 VERIFICACIÓN ESPECÍFICA - Proyectos del 26/08/2025")
print("-" * 40)

proyectos_26_agosto = [
    "Planta de Tratamiento de Aguas",
    "Proyecto Inmobiliario",
    "Parque Solar",
    "Central Fotovoltaica"
]

encontrados = 0
for proyecto_buscado in proyectos_26_agosto:
    encontrado = False
    for p in proyectos_sea + proyectos_int:
        if proyecto_buscado.lower() in p.get('titulo', '').lower():
            encontrado = True
            encontrados += 1
            break
    
    estado = "✅" if encontrado else "❌"
    print(f"{estado} {proyecto_buscado}")

print(f"\nProyectos específicos encontrados: {encontrados}/{len(proyectos_26_agosto)}")

if encontrados < len(proyectos_26_agosto):
    print("\n⚠️ No se encontraron todos los proyectos del 26/08")
    print("El scraper SEA necesita más ajustes para capturar todos los proyectos")