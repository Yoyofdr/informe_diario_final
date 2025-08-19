#!/usr/bin/env python3
"""
Script de verificación del sistema de envío automático de informes
"""
import os
import sys
from datetime import datetime
import pytz

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
import django
django.setup()

from alerts.models import Destinatario, InformeDiarioCache
from alerts.utils.cache_informe import CacheInformeDiario
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def verificar_sistema():
    """Verifica que todo esté configurado correctamente"""
    
    print("=" * 70)
    print("VERIFICACIÓN DEL SISTEMA DE ENVÍO AUTOMÁTICO DE INFORMES")
    print("=" * 70)
    print()
    
    errores = []
    advertencias = []
    ok = []
    
    # 1. Verificar variables de entorno críticas
    print("1. VERIFICANDO VARIABLES DE ENTORNO...")
    print("-" * 40)
    
    vars_requeridas = {
        'HOSTINGER_EMAIL_PASSWORD': 'Contraseña del email',
        'OPENAI_API_KEY': 'API Key de OpenAI',
        'SMTP_SERVER': 'Servidor SMTP (opcional)',
        'SMTP_PORT': 'Puerto SMTP (opcional)'
    }
    
    for var, descripcion in vars_requeridas.items():
        valor = os.getenv(var)
        if valor:
            if var == 'OPENAI_API_KEY':
                print(f"   ✅ {var}: {valor[:20]}...")
            elif var == 'HOSTINGER_EMAIL_PASSWORD':
                print(f"   ✅ {var}: {'*' * 8}")
            else:
                print(f"   ✅ {var}: {valor}")
            ok.append(f"{descripcion} configurado")
        else:
            if 'opcional' in descripcion.lower():
                print(f"   ⚠️ {var}: No configurado (usando valor por defecto)")
                advertencias.append(f"{descripcion} no configurado")
            else:
                print(f"   ❌ {var}: FALTANTE")
                errores.append(f"{descripcion} no está configurado")
    
    print()
    
    # 2. Verificar destinatarios
    print("2. VERIFICANDO DESTINATARIOS...")
    print("-" * 40)
    
    destinatarios = Destinatario.objects.all()
    total_destinatarios = destinatarios.count()
    
    if total_destinatarios > 0:
        print(f"   ✅ Total de destinatarios: {total_destinatarios}")
        ok.append(f"{total_destinatarios} destinatarios configurados")
        
        # Mostrar primeros 5
        print("   Primeros destinatarios:")
        for dest in destinatarios[:5]:
            print(f"      - {dest.email} ({dest.nombre})")
        if total_destinatarios > 5:
            print(f"      ... y {total_destinatarios - 5} más")
    else:
        print(f"   ❌ No hay destinatarios registrados")
        errores.append("No hay destinatarios en la base de datos")
    
    print()
    
    # 3. Verificar caché de informes
    print("3. VERIFICANDO SISTEMA DE CACHÉ...")
    print("-" * 40)
    
    cache = CacheInformeDiario()
    chile_tz = pytz.timezone('America/Santiago')
    fecha_hoy = datetime.now(chile_tz).date()
    
    if cache.existe_informe_hoy():
        print(f"   ✅ Existe informe de hoy ({fecha_hoy}) en caché")
        ok.append("Informe de hoy disponible en caché")
        
        informe = cache.obtener_informe()
        if informe:
            print(f"      Tamaño: {len(informe)} caracteres")
    else:
        hora_actual = datetime.now(chile_tz).hour
        if hora_actual < 9:
            print(f"   ⚠️ No hay informe de hoy (normal antes de las 9:00 AM)")
            advertencias.append("Informe aún no generado (es antes de las 9 AM)")
        else:
            print(f"   ⚠️ No hay informe de hoy en caché")
            advertencias.append("No hay informe de hoy en caché")
    
    # Verificar informes anteriores
    informes_totales = InformeDiarioCache.objects.count()
    if informes_totales > 0:
        print(f"   ✅ Total de informes en caché: {informes_totales}")
        ultimo_informe = InformeDiarioCache.objects.latest('fecha')
        print(f"      Último informe: {ultimo_informe.fecha}")
    
    print()
    
    # 4. Verificar archivos necesarios
    print("4. VERIFICANDO ARCHIVOS DEL SISTEMA...")
    print("-" * 40)
    
    archivos_requeridos = [
        'scripts/generators/generar_informe_oficial_integrado_mejorado.py',
        'alerts/enviar_informe_bienvenida.py',
        'alerts/utils/cache_informe.py',
        'alerts/scraper_diario_oficial.py'
    ]
    
    for archivo in archivos_requeridos:
        ruta_completa = os.path.join(os.path.dirname(__file__), archivo)
        if os.path.exists(ruta_completa):
            print(f"   ✅ {archivo}")
            ok.append(f"Archivo {archivo} existe")
        else:
            print(f"   ❌ {archivo} - NO ENCONTRADO")
            errores.append(f"Archivo {archivo} no encontrado")
    
    print()
    
    # 5. Información del scheduler
    print("5. CONFIGURACIÓN DEL SCHEDULER...")
    print("-" * 40)
    print("   ℹ️ El Heroku Scheduler debe estar configurado con:")
    print("      Comando: python scripts/generators/generar_informe_oficial_integrado_mejorado.py")
    print("      Horario: Daily at 12:00 PM UTC (9:00 AM Chile)")
    print()
    print("   Para verificar, ejecuta:")
    print("      heroku addons:open scheduler --app informediariochile")
    
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    
    if ok:
        print(f"\n✅ ELEMENTOS CORRECTOS ({len(ok)}):")
        for item in ok:
            print(f"   • {item}")
    
    if advertencias:
        print(f"\n⚠️ ADVERTENCIAS ({len(advertencias)}):")
        for item in advertencias:
            print(f"   • {item}")
    
    if errores:
        print(f"\n❌ ERRORES CRÍTICOS ({len(errores)}):")
        for item in errores:
            print(f"   • {item}")
        print("\n⚠️ ACCIÓN REQUERIDA: Corrige los errores antes del próximo envío")
    else:
        print("\n✅ SISTEMA LISTO PARA ENVÍO AUTOMÁTICO")
    
    print("=" * 70)
    
    return len(errores) == 0

if __name__ == "__main__":
    sys.exit(0 if verificar_sistema() else 1)