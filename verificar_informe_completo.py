#!/usr/bin/env python
"""
Verificación completa del sistema de informes
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.utils import timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print("🔍 VERIFICACIÓN COMPLETA DEL SISTEMA DE INFORMES")
print(f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*70)

# 1. VERIFICAR SCRAPERS
print("\n📊 1. VERIFICANDO SCRAPERS...")
print("-"*70)

scrapers_status = {
    "Diario Oficial": False,
    "CMF": False,
    "SII": False,
    "Medio Ambiente (SEA/SMA)": False,
    "Proyectos de Ley": False,
    "Reglamentos": False
}

# Probar Diario Oficial
try:
    from scripts.scrapers.scraper_diario_oficial_mejorado import ScraperDiarioOficial
    scraper = ScraperDiarioOficial()
    publicaciones = scraper.obtener_publicaciones(dias_atras=1)
    if publicaciones:
        scrapers_status["Diario Oficial"] = True
        print(f"✅ Diario Oficial: {len(publicaciones)} publicaciones")
    else:
        print("⚠️ Diario Oficial: Sin publicaciones recientes")
except Exception as e:
    print(f"❌ Diario Oficial: Error - {str(e)[:50]}")

# Probar CMF
try:
    from scripts.scrapers.scraper_cmf_mejorado import ScraperCMF
    scraper = ScraperCMF()
    documentos = scraper.obtener_documentos(dias_atras=1)
    if documentos:
        scrapers_status["CMF"] = True
        print(f"✅ CMF: {len(documentos)} documentos")
    else:
        print("⚠️ CMF: Sin documentos recientes")
except Exception as e:
    print(f"❌ CMF: Error - {str(e)[:50]}")

# Probar SII
try:
    from scripts.scrapers.scraper_sii_completo import ScraperSII
    scraper = ScraperSII()
    documentos = scraper.obtener_documentos_sii(dias_atras=1)
    if documentos:
        scrapers_status["SII"] = True
        print(f"✅ SII: {len(documentos)} documentos")
    else:
        print("⚠️ SII: Sin documentos recientes")
except Exception as e:
    print(f"❌ SII: Error - {str(e)[:50]}")

# Probar Medio Ambiente
try:
    from scripts.scrapers.scraper_ambiental_integrado import ScraperAmbiental
    scraper = ScraperAmbiental()
    datos = scraper.obtener_datos_ambientales(dias_atras=7)
    total = len(datos.get('proyectos_sea', [])) + len(datos.get('sanciones_sma', []))
    if total > 0:
        scrapers_status["Medio Ambiente (SEA/SMA)"] = True
        print(f"✅ Medio Ambiente: {len(datos.get('proyectos_sea', []))} SEA, {len(datos.get('sanciones_sma', []))} SMA")
    else:
        print("⚠️ Medio Ambiente: Sin datos recientes")
except Exception as e:
    print(f"❌ Medio Ambiente: Error - {str(e)[:50]}")

# Probar Proyectos de Ley
try:
    from scripts.scrapers.scraper_proyectos_ley import ScraperProyectosLey
    scraper = ScraperProyectosLey()
    proyectos = scraper.obtener_proyectos(dias_atras=7)
    if proyectos:
        scrapers_status["Proyectos de Ley"] = True
        print(f"✅ Proyectos de Ley: {len(proyectos)} proyectos")
    else:
        print("⚠️ Proyectos de Ley: Sin proyectos recientes")
except Exception as e:
    print(f"❌ Proyectos de Ley: Error - {str(e)[:50]}")

# Probar Reglamentos
try:
    from scripts.scrapers.scraper_reglamentos import ScraperReglamentos
    scraper = ScraperReglamentos()
    reglamentos = scraper.obtener_reglamentos(dias_atras=7)
    if reglamentos:
        scrapers_status["Reglamentos"] = True
        print(f"✅ Reglamentos: {len(reglamentos)} reglamentos")
    else:
        print("⚠️ Reglamentos: Sin reglamentos recientes")
except Exception as e:
    print(f"❌ Reglamentos: Error - {str(e)[:50]}")

# 2. VERIFICAR GENERACIÓN DE INFORME
print("\n📝 2. VERIFICANDO GENERACIÓN DE INFORME...")
print("-"*70)

try:
    from generar_informe_oficial_integrado_mejorado import generar_informe_completo
    
    # Simular generación de informe
    print("Generando informe de prueba...")
    contenido = generar_informe_completo(test_mode=True)
    
    if contenido:
        print("✅ Informe generado correctamente")
        
        # Verificar secciones
        secciones = [
            "RESUMEN EJECUTIVO",
            "DIARIO OFICIAL",
            "COMISIÓN PARA EL MERCADO FINANCIERO",
            "SERVICIO DE IMPUESTOS INTERNOS",
            "MEDIO AMBIENTE",
            "PROYECTOS DE LEY",
            "REGLAMENTOS Y DECRETOS"
        ]
        
        print("\nSecciones del informe:")
        for seccion in secciones:
            if seccion in contenido:
                print(f"  ✅ {seccion}")
            else:
                print(f"  ❌ {seccion} - FALTA")
    else:
        print("❌ No se pudo generar el informe")
        
except Exception as e:
    print(f"❌ Error generando informe: {str(e)}")

# 3. VERIFICAR SISTEMA DE ENVÍOS
print("\n📧 3. VERIFICANDO SISTEMA DE ENVÍOS...")
print("-"*70)

try:
    from alerts.models import Destinatario
    
    # Contar destinatarios activos
    destinatarios = Destinatario.objects.filter(activo=True)
    total = destinatarios.count()
    
    # Verificar trials
    con_trial = destinatarios.filter(
        es_pagado=False,
        fecha_fin_trial__gte=timezone.now()
    ).count()
    
    pagados = destinatarios.filter(es_pagado=True).count()
    trial_vencido = total - con_trial - pagados
    
    print(f"✅ Total destinatarios activos: {total}")
    print(f"  - Clientes pagados: {pagados}")
    print(f"  - En período de prueba: {con_trial}")
    print(f"  - Trial vencido: {trial_vencido}")
    
except Exception as e:
    print(f"❌ Error verificando destinatarios: {str(e)}")

# 4. VERIFICAR CONFIGURACIÓN
print("\n⚙️ 4. VERIFICANDO CONFIGURACIÓN...")
print("-"*70)

# Verificar variables de entorno críticas
env_vars = {
    "OPENAI_API_KEY": os.environ.get('OPENAI_API_KEY', ''),
    "EMAIL_HOST_USER": os.environ.get('EMAIL_HOST_USER', ''),
    "EMAIL_HOST_PASSWORD": os.environ.get('EMAIL_HOST_PASSWORD', ''),
    "DATABASE_URL": os.environ.get('DATABASE_URL', ''),
}

for var, value in env_vars.items():
    if value:
        print(f"✅ {var}: Configurado")
    else:
        print(f"❌ {var}: NO configurado")

# 5. RESUMEN FINAL
print("\n" + "="*70)
print("📊 RESUMEN FINAL")
print("="*70)

total_scrapers = len(scrapers_status)
scrapers_ok = sum(1 for v in scrapers_status.values() if v)

print(f"\nScrapers funcionando: {scrapers_ok}/{total_scrapers}")
for scraper, status in scrapers_status.items():
    emoji = "✅" if status else "❌"
    print(f"  {emoji} {scraper}")

if scrapers_ok == total_scrapers:
    print("\n✅ SISTEMA LISTO PARA ENVÍO DE INFORMES")
else:
    print(f"\n⚠️ ATENCIÓN: {total_scrapers - scrapers_ok} scrapers no están funcionando")
    print("Los informes se generarán con datos de ejemplo para las secciones faltantes")

print("\n📌 Próximo envío programado: Mañana a las 9:00 AM hora Chile")
print("="*70)