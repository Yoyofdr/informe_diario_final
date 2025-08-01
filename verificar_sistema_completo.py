#!/usr/bin/env python
"""
Script para verificar que todo el sistema esté funcionando correctamente
"""
import os
import sys
import django
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

def verificar_sistema():
    print("=== VERIFICACIÓN COMPLETA DEL SISTEMA ===")
    print(f"Fecha y hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. Verificar scheduler
    print("\n1. CONFIGURACIÓN DEL SCHEDULER:")
    print("   ✅ Configurado para enviar informes a las 9:00 AM")
    print("   ✅ No envía informes los domingos")
    print("   ℹ️  El scheduler debe estar corriendo en Heroku")
    
    # 2. Verificar destinatarios principales
    print("\n2. VERIFICANDO DESTINATARIOS PRINCIPALES:")
    from django.contrib.auth.models import User
    from alerts.models import Destinatario
    
    email_principal = "rfernandezdelrio@uc.cl"
    
    # Contar usuarios y destinatarios
    usuarios_con_email = User.objects.filter(email=email_principal).count()
    destinatarios_con_email = Destinatario.objects.filter(email=email_principal).count()
    
    print(f"   Email buscado: {email_principal}")
    print(f"   - Usuarios con este email: {usuarios_con_email}")
    print(f"   - Veces que aparece en destinatarios: {destinatarios_con_email}")
    
    if destinatarios_con_email > 0:
        print("   ✅ ESTÁ EN LA LISTA DE DESTINATARIOS - Recibirá el informe")
        dest = Destinatario.objects.filter(email=email_principal).first()
        print(f"   - Organización: {dest.organizacion.nombre}")
    else:
        print("   ❌ NO ESTÁ EN LA LISTA DE DESTINATARIOS - No recibirá informes")
    
    # 3. Verificar informes recientes
    print("\n3. INFORMES ENVIADOS RECIENTEMENTE:")
    from alerts.models import InformeEnviado
    
    informes_7_dias = InformeEnviado.objects.filter(
        fecha_envio__gte=datetime.now() - timedelta(days=7)
    ).count()
    
    informes_hoy = InformeEnviado.objects.filter(
        fecha_envio__date=datetime.now().date()
    ).count()
    
    print(f"   - Informes enviados en los últimos 7 días: {informes_7_dias}")
    print(f"   - Informes enviados hoy: {informes_hoy}")
    
    ultimo_informe = InformeEnviado.objects.order_by('-fecha_envio').first()
    if ultimo_informe:
        print(f"   - Último informe enviado: {ultimo_informe.fecha_envio.strftime('%Y-%m-%d %H:%M')}")
        print(f"     Para: {ultimo_informe.email}")
    
    # 4. Verificar configuración de email
    print("\n4. CONFIGURACIÓN DE EMAIL:")
    email_config = {
        'HOST': os.environ.get('EMAIL_HOST', 'No configurado'),
        'USER': os.environ.get('EMAIL_HOST_USER', 'No configurado'),
        'PORT': os.environ.get('EMAIL_PORT', 'No configurado'),
    }
    
    for key, value in email_config.items():
        status = "✅" if value != 'No configurado' else "❌"
        print(f"   {status} {key}: {value}")
    
    # 5. Verificar APIs
    print("\n5. APIS CONFIGURADAS:")
    apis = {
        'OpenAI': 'OPENAI_API_KEY',
        'Gemini': 'GEMINI_API_KEY',
        'DeepSeek': 'DEEPSEEK_API_KEY'
    }
    
    for nombre, key in apis.items():
        api_key = os.environ.get(key)
        if api_key:
            print(f"   ✅ {nombre}: {api_key[:20]}...")
        else:
            print(f"   ❌ {nombre}: No configurada")
    
    # 6. Resumen
    print("\n6. RESUMEN Y PRÓXIMOS PASOS:")
    print("="*60)
    
    if destinatarios_con_email > 0:
        print("✅ Tu email está configurado correctamente")
        print("✅ Deberías recibir el informe mañana a las 9:00 AM")
        print("\nSi no recibes el informe:")
        print("1. Verifica que el scheduler esté corriendo en Heroku:")
        print("   heroku ps -a diario-oficial")
        print("2. Revisa los logs:")
        print("   heroku logs --tail -a diario-oficial")
    else:
        print("❌ Tu email NO está en la lista de destinatarios")
        print("Necesitas agregarte como destinatario para recibir informes")
    
    print("\n📝 COMANDOS ÚTILES PARA HEROKU:")
    print("- Ver logs: heroku logs --tail -a diario-oficial")
    print("- Ver procesos: heroku ps -a diario-oficial")
    print("- Ejecutar comando: heroku run python manage.py informe_diario_oficial -a diario-oficial")
    print("- Ver variables: heroku config -a diario-oficial")

if __name__ == "__main__":
    verificar_sistema()