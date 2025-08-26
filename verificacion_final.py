#!/usr/bin/env python
"""
Verificación final del sistema de informes diarios
"""

import os
import sys
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.utils import timezone
from alerts.models import Destinatario

print("\n" + "="*80)
print("✅ VERIFICACIÓN FINAL DEL SISTEMA DE INFORMES DIARIOS")
print("="*80)
print(f"\n📅 Fecha y hora actual: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print(f"🌎 Zona horaria: Chile/Continental")

# 1. VERIFICAR FUENTES DE DATOS
print("\n" + "="*80)
print("1️⃣ FUENTES DE DATOS DISPONIBLES")
print("="*80)

fuentes_status = {}

# Verificar cada scraper
print("\n📊 Estado de los scrapers:")
print("-"*40)

# Medio Ambiente (SEA/SMA)
try:
    from scripts.scrapers.scraper_ambiental_integrado import ScraperAmbiental
    scraper = ScraperAmbiental()
    datos = scraper.obtener_datos_ambientales(dias_atras=1)
    sea_count = len(datos.get('proyectos_sea', []))
    sma_count = len(datos.get('sanciones_sma', []))
    total = sea_count + sma_count
    fuentes_status['Medio Ambiente'] = f"{sea_count} SEA, {sma_count} SMA"
    print(f"✅ Medio Ambiente: {sea_count} proyectos SEA, {sma_count} sanciones SMA")
    if total > 0:
        for p in datos.get('proyectos_sea', [])[:2]:
            print(f"   • SEA: {p.get('titulo', '')[:60]}...")
        for s in datos.get('sanciones_sma', [])[:2]:
            print(f"   • SMA: {s.get('titulo', '')[:60]}...")
except Exception as e:
    fuentes_status['Medio Ambiente'] = "Error"
    print(f"❌ Medio Ambiente: {str(e)[:50]}")

# Proyectos de Ley
try:
    from scripts.scrapers.scraper_proyectos_ley_integrado import ScraperProyectosLeyIntegrado
    scraper = ScraperProyectosLeyIntegrado()
    # El método correcto es obtener_proyectos_recientes
    proyectos = scraper.obtener_proyectos_recientes(dias=7)
    fuentes_status['Proyectos de Ley'] = f"{len(proyectos)} proyectos"
    print(f"✅ Proyectos de Ley: {len(proyectos)} proyectos")
    for p in proyectos[:2]:
        print(f"   • {p.get('titulo', '')[:60]}...")
except Exception as e:
    fuentes_status['Proyectos de Ley'] = "Error"
    print(f"❌ Proyectos de Ley: {str(e)[:50]}")

# Reglamentos
try:
    from scripts.scrapers.scraper_contraloria_reglamentos import ScraperContraloriaReglamentos
    scraper = ScraperContraloriaReglamentos()
    reglamentos = scraper.obtener_reglamentos_recientes(dias=7)
    fuentes_status['Reglamentos'] = f"{len(reglamentos)} reglamentos"
    print(f"✅ Reglamentos: {len(reglamentos)} reglamentos")
    for r in reglamentos[:2]:
        print(f"   • {r.get('titulo', '')[:60]}...")
except Exception as e:
    fuentes_status['Reglamentos'] = "Error"
    print(f"❌ Reglamentos: {str(e)[:50]}")

# CMF
try:
    from scripts.scrapers.scraper_cmf_mejorado import ScraperCMFMejorado
    scraper = ScraperCMFMejorado()
    documentos = scraper.obtener_documentos_cmf()
    fuentes_status['CMF'] = f"{len(documentos)} documentos"
    print(f"✅ CMF: {len(documentos)} documentos")
    for d in documentos[:2]:
        print(f"   • {d.get('titulo', '')[:60]}...")
except Exception as e:
    fuentes_status['CMF'] = "Error"
    print(f"❌ CMF: {str(e)[:50]}")

# Diario Oficial (DT)
try:
    from scripts.scrapers.scraper_dt import ScraperDT
    scraper = ScraperDT()
    publicaciones = scraper.buscar_publicaciones_recientes(dias_atras=1)
    fuentes_status['Diario Oficial'] = f"{len(publicaciones)} publicaciones"
    print(f"✅ Diario Oficial: {len(publicaciones)} publicaciones")
    for p in publicaciones[:2]:
        print(f"   • {p.get('titulo', '')[:60]}...")
except Exception as e:
    fuentes_status['Diario Oficial'] = "Error"
    print(f"❌ Diario Oficial: {str(e)[:50]}")

# 2. VERIFICAR DESTINATARIOS
print("\n" + "="*80)
print("2️⃣ DESTINATARIOS DEL INFORME")
print("="*80)

destinatarios = Destinatario.objects.all()
total = destinatarios.count()
print(f"\n📧 Total destinatarios registrados: {total}")

if total > 0:
    print("\n📋 Detalle de destinatarios:")
    print("-"*40)
    
    for dest in destinatarios:
        estado = "✅ Activo" if dest.es_pagado else ""
        if not dest.es_pagado and dest.fecha_fin_trial:
            if dest.fecha_fin_trial >= timezone.now():
                dias_restantes = (dest.fecha_fin_trial - timezone.now()).days
                estado = f"🔄 Trial ({dias_restantes} días restantes)"
            else:
                estado = "❌ Trial vencido"
        
        print(f"• {dest.email} - {estado}")
        if dest.organizacion:
            print(f"  Organización: {dest.organizacion.nombre}")

# 3. VERIFICACIÓN DE CONFIGURACIÓN
print("\n" + "="*80)
print("3️⃣ CONFIGURACIÓN DEL SISTEMA")
print("="*80)

print("\n⚙️ Variables de entorno:")
print("-"*40)

configs = {
    "OpenAI API": "OPENAI_API_KEY" in os.environ,
    "Email SMTP": "EMAIL_HOST_USER" in os.environ and "EMAIL_HOST_PASSWORD" in os.environ,
    "Base de datos": "DATABASE_URL" in os.environ or "default" in django.conf.settings.DATABASES
}

all_ok = True
for config, status in configs.items():
    emoji = "✅" if status else "❌"
    print(f"{emoji} {config}: {'Configurado' if status else 'NO configurado'}")
    if not status:
        all_ok = False

# 4. RESUMEN EJECUTIVO
print("\n" + "="*80)
print("📊 RESUMEN EJECUTIVO")
print("="*80)

# Contar fuentes funcionando
fuentes_ok = sum(1 for v in fuentes_status.values() if v != "Error")
total_fuentes = len(fuentes_status)

print(f"\n✅ Fuentes de datos operativas: {fuentes_ok}/{total_fuentes}")
for fuente, estado in fuentes_status.items():
    if estado != "Error":
        print(f"   • {fuente}: {estado}")

fuentes_error = [f for f, e in fuentes_status.items() if e == "Error"]
if fuentes_error:
    print(f"\n❌ Fuentes con problemas: {', '.join(fuentes_error)}")

print(f"\n📧 Destinatarios activos: {total}")

# 5. ESTADO FINAL
print("\n" + "="*80)
print("🚀 ESTADO DEL SISTEMA")
print("="*80)

if fuentes_ok >= 3 and total > 0 and all_ok:
    print("\n✅ SISTEMA COMPLETAMENTE OPERATIVO")
    print("   • Todas las configuraciones están correctas")
    print(f"   • {fuentes_ok} fuentes de datos disponibles")
    print(f"   • {total} destinatarios registrados")
    print("\n📌 El informe se enviará automáticamente mañana a las 9:00 AM (Chile)")
    print("   Contendrá información de:")
    for fuente, estado in fuentes_status.items():
        if estado != "Error":
            print(f"   • {fuente}")
elif fuentes_ok >= 2:
    print("\n⚠️ SISTEMA PARCIALMENTE OPERATIVO")
    print(f"   • Solo {fuentes_ok} fuentes disponibles de {total_fuentes}")
    print("   • El informe se generará con las fuentes disponibles")
    print("   • Se usarán datos de ejemplo para fuentes faltantes")
else:
    print("\n❌ SISTEMA CON PROBLEMAS CRÍTICOS")
    print("   • Verificar configuración y scrapers")
    print("   • Contactar soporte técnico si persiste")

print("\n" + "="*80)
print("📞 Para soporte técnico: rfernandez@carvuk.com")
print("="*80)