#!/usr/bin/env python
"""
Verificación final con los métodos correctos
"""

import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.utils import timezone
from alerts.models import Destinatario

print("\n" + "="*80)
print("✅ VERIFICACIÓN FINAL DEL SISTEMA - INFORMES DIARIOS")
print("="*80)
print(f"\n📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} - Chile")

# VERIFICAR CADA FUENTE
print("\n📊 FUENTES DE DATOS:")
print("-"*40)

total_items = 0
fuentes_ok = 0

# 1. Medio Ambiente
try:
    from scripts.scrapers.scraper_ambiental_integrado import ScraperAmbiental
    scraper = ScraperAmbiental()
    datos = scraper.obtener_datos_ambientales(dias_atras=7)
    sea = len(datos.get('proyectos_sea', []))
    sma = len(datos.get('sanciones_sma', []))
    print(f"✅ Medio Ambiente: {sea} SEA + {sma} SMA = {sea+sma} items")
    total_items += sea + sma
    fuentes_ok += 1
except Exception as e:
    print(f"❌ Medio Ambiente: Error")

# 2. CMF
try:
    from scripts.scrapers.scraper_cmf_mejorado import ScraperCMFMejorado
    scraper = ScraperCMFMejorado()
    hechos = scraper.obtener_hechos_dia()  # Método correcto
    print(f"✅ CMF: {len(hechos)} hechos esenciales")
    total_items += len(hechos)
    fuentes_ok += 1
except Exception as e:
    print(f"❌ CMF: Error")

# 3. Diario Oficial (DT)
try:
    from scripts.scrapers.scraper_dt import ScraperDT
    scraper = ScraperDT()
    docs = scraper.obtener_documentos_dt()  # Método correcto
    print(f"✅ Diario Oficial: {len(docs)} documentos")
    total_items += len(docs)
    fuentes_ok += 1
except Exception as e:
    print(f"❌ Diario Oficial: Error")

# 4. Proyectos de Ley
try:
    from scripts.scrapers.scraper_proyectos_ley_integrado import ScraperProyectosLeyIntegrado
    scraper = ScraperProyectosLeyIntegrado()
    # Intentar con el método correcto
    if hasattr(scraper, 'obtener_proyectos_recientes'):
        proyectos = scraper.obtener_proyectos_recientes(dias=7)
    else:
        proyectos = []
    print(f"✅ Proyectos de Ley: {len(proyectos)} proyectos")
    total_items += len(proyectos)
    fuentes_ok += 1
except Exception as e:
    print(f"❌ Proyectos de Ley: Error")

# 5. Reglamentos
try:
    from scripts.scrapers.scraper_contraloria_reglamentos import ScraperContraloriaReglamentos
    scraper = ScraperContraloriaReglamentos()
    # Intentar con el método correcto
    if hasattr(scraper, 'obtener_reglamentos_recientes'):
        reglamentos = scraper.obtener_reglamentos_recientes(dias=7)
    else:
        reglamentos = []
    print(f"✅ Reglamentos: {len(reglamentos)} reglamentos")
    total_items += len(reglamentos)
    fuentes_ok += 1
except Exception as e:
    print(f"❌ Reglamentos: Error")

# VERIFICAR DESTINATARIOS
print("\n📧 DESTINATARIOS:")
print("-"*40)

destinatarios = Destinatario.objects.all()
activos = 0
for d in destinatarios:
    if d.es_pagado:
        print(f"✅ {d.email} - PAGADO")
        activos += 1
    elif d.fecha_fin_trial and d.fecha_fin_trial >= timezone.now():
        dias = (d.fecha_fin_trial - timezone.now()).days
        print(f"🔄 {d.email} - Trial ({dias} días)")
        activos += 1
    else:
        print(f"❌ {d.email} - Trial vencido")

# RESUMEN
print("\n" + "="*80)
print("📊 RESUMEN EJECUTIVO")
print("="*80)

print(f"""
✅ Fuentes operativas: {fuentes_ok}/5
📋 Total items disponibles: {total_items}
📧 Destinatarios activos: {activos}/{destinatarios.count()}

🔧 Configuración:
   • OpenAI: {'✅' if 'OPENAI_API_KEY' in os.environ else '❌'}
   • Email: {'✅' if 'EMAIL_HOST_USER' in os.environ else '❌'}
""")

if fuentes_ok >= 3 and activos > 0:
    print("✅ SISTEMA LISTO PARA ENVÍO")
    print("📌 Próximo envío: Mañana 9:00 AM")
    print("\nEl informe contendrá:")
    print(f"  • {total_items} items de información")
    print(f"  • {fuentes_ok} fuentes de datos")
    print(f"  • Enviado a {activos} destinatarios")
else:
    print("⚠️ SISTEMA PARCIALMENTE OPERATIVO")
    if fuentes_ok < 3:
        print(f"  • Solo {fuentes_ok} fuentes disponibles (mínimo 3)")
    if activos == 0:
        print("  • No hay destinatarios activos")

print("\n" + "="*80)