#!/usr/bin/env python
"""
Verificación real del sistema de informes con los archivos correctos
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

scrapers_status = {}

# Scrapers CMF y DT (principales)
try:
    from scripts.scrapers.scraper_cmf_mejorado import obtener_documentos_cmf_con_contenido
    documentos = obtener_documentos_cmf_con_contenido(dias_atras=1)
    if documentos:
        scrapers_status["CMF"] = len(documentos)
        print(f"✅ CMF: {len(documentos)} documentos")
    else:
        scrapers_status["CMF"] = 0
        print("⚠️ CMF: Sin documentos recientes")
except Exception as e:
    scrapers_status["CMF"] = -1
    print(f"❌ CMF: Error - {str(e)[:50]}")

try:
    from scripts.scrapers.scraper_dt import ScraperDiarioOficial
    scraper = ScraperDiarioOficial()
    publicaciones = scraper.obtener_publicaciones(dias_atras=1)
    if publicaciones:
        scrapers_status["Diario Oficial"] = len(publicaciones)
        print(f"✅ Diario Oficial: {len(publicaciones)} publicaciones")
    else:
        scrapers_status["Diario Oficial"] = 0
        print("⚠️ Diario Oficial: Sin publicaciones recientes")
except Exception as e:
    scrapers_status["Diario Oficial"] = -1
    print(f"❌ Diario Oficial: Error - {str(e)[:50]}")

# Medio Ambiente (SEA/SMA)
try:
    from scripts.scrapers.scraper_ambiental_integrado import ScraperAmbiental
    scraper = ScraperAmbiental()
    datos = scraper.obtener_datos_ambientales(dias_atras=7)
    total = len(datos.get('proyectos_sea', [])) + len(datos.get('sanciones_sma', []))
    scrapers_status["Medio Ambiente"] = total
    print(f"✅ Medio Ambiente: {len(datos.get('proyectos_sea', []))} SEA, {len(datos.get('sanciones_sma', []))} SMA")
except Exception as e:
    scrapers_status["Medio Ambiente"] = -1
    print(f"❌ Medio Ambiente: Error - {str(e)[:50]}")

# Proyectos de Ley
try:
    from scripts.scrapers.scraper_proyectos_ley_integrado import ScraperProyectosLeyIntegrado
    scraper = ScraperProyectosLeyIntegrado()
    proyectos = scraper.obtener_todos_los_proyectos(dias_atras=7)
    scrapers_status["Proyectos de Ley"] = len(proyectos)
    print(f"✅ Proyectos de Ley: {len(proyectos)} proyectos")
except Exception as e:
    scrapers_status["Proyectos de Ley"] = -1
    print(f"❌ Proyectos de Ley: Error - {str(e)[:50]}")

# Reglamentos (Contraloría)
try:
    from scripts.scrapers.scraper_contraloria_reglamentos import ScraperContraloria
    scraper = ScraperContraloria()
    reglamentos = scraper.obtener_reglamentos_recientes(dias_atras=7)
    scrapers_status["Reglamentos"] = len(reglamentos)
    print(f"✅ Reglamentos: {len(reglamentos)} reglamentos")
except Exception as e:
    scrapers_status["Reglamentos"] = -1
    print(f"❌ Reglamentos: Error - {str(e)[:50]}")

# 2. VERIFICAR GENERACIÓN DE INFORME
print("\n📝 2. VERIFICANDO GENERACIÓN DE INFORME...")
print("-"*70)

try:
    from scripts.generators.generar_informe_oficial_integrado_mejorado import generar_informe_completo
    
    # Simular generación de informe
    print("Generando informe de prueba (sin enviar)...")
    contenido = generar_informe_completo(test_mode=True)
    
    if contenido:
        print("✅ Informe generado correctamente")
        
        # Verificar secciones
        secciones_esperadas = [
            "RESUMEN EJECUTIVO",
            "COMISIÓN PARA EL MERCADO FINANCIERO",
            "DIARIO OFICIAL",
            "MEDIO AMBIENTE",
            "PROYECTOS DE LEY", 
            "REGLAMENTOS"
        ]
        
        print("\nSecciones del informe:")
        for seccion in secciones_esperadas:
            if seccion in contenido:
                print(f"  ✅ {seccion}")
            else:
                print(f"  ⚠️ {seccion} - No encontrada")
    else:
        print("❌ No se pudo generar el informe")
        
except Exception as e:
    print(f"❌ Error generando informe: {str(e)}")

# 3. VERIFICAR SISTEMA DE ENVÍOS
print("\n📧 3. VERIFICANDO SISTEMA DE ENVÍOS...")
print("-"*70)

try:
    from alerts.models import Destinatario
    
    # Contar destinatarios
    destinatarios = Destinatario.objects.all()
    total = destinatarios.count()
    
    # Verificar trials
    con_trial = destinatarios.filter(
        es_pagado=False,
        fecha_fin_trial__gte=timezone.now()
    ).count()
    
    pagados = destinatarios.filter(es_pagado=True).count()
    trial_vencido = destinatarios.filter(
        es_pagado=False,
        fecha_fin_trial__lt=timezone.now()
    ).count()
    
    print(f"✅ Total destinatarios: {total}")
    print(f"  - Clientes pagados: {pagados}")
    print(f"  - En período de prueba activo: {con_trial}")
    print(f"  - Trial vencido: {trial_vencido}")
    
    # Mostrar próximos vencimientos
    proximos_vencer = destinatarios.filter(
        es_pagado=False,
        fecha_fin_trial__gte=timezone.now(),
        fecha_fin_trial__lte=timezone.now() + timedelta(days=3)
    )
    
    if proximos_vencer.exists():
        print("\n⚠️ Trials próximos a vencer (3 días):")
        for dest in proximos_vencer:
            dias_restantes = (dest.fecha_fin_trial - timezone.now()).days
            print(f"  - {dest.email}: {dias_restantes} días restantes")
    
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
}

config_ok = True
for var, value in env_vars.items():
    if value:
        print(f"✅ {var}: Configurado")
    else:
        print(f"❌ {var}: NO configurado")
        config_ok = False

# 5. RESUMEN FINAL
print("\n" + "="*70)
print("📊 RESUMEN FINAL DEL SISTEMA")
print("="*70)

# Contar scrapers funcionando
scrapers_ok = sum(1 for v in scrapers_status.values() if v > 0)
scrapers_error = sum(1 for v in scrapers_status.values() if v == -1)
scrapers_sin_datos = sum(1 for v in scrapers_status.values() if v == 0)

print(f"\n📋 Estado de Scrapers:")
print(f"  - Funcionando: {scrapers_ok}/{len(scrapers_status)}")
print(f"  - Sin datos recientes: {scrapers_sin_datos}")
print(f"  - Con errores: {scrapers_error}")

print("\n📊 Detalle por fuente:")
for scraper, count in scrapers_status.items():
    if count > 0:
        print(f"  ✅ {scraper}: {count} items")
    elif count == 0:
        print(f"  ⚠️ {scraper}: Sin datos")
    else:
        print(f"  ❌ {scraper}: Error")

# Evaluación final
print("\n" + "="*70)
if scrapers_ok >= 3 and config_ok:
    print("✅ SISTEMA OPERATIVO - Listo para envío de informes")
    print("📌 Próximo envío: Mañana 9:00 AM (Chile)")
elif scrapers_ok >= 2:
    print("⚠️ SISTEMA PARCIALMENTE OPERATIVO")
    print("   Algunas fuentes no están disponibles")
    print("   Los informes se generarán con las fuentes disponibles")
else:
    print("❌ SISTEMA CON PROBLEMAS CRÍTICOS")
    print("   Revisar scrapers y configuración")

print("="*70)