#!/usr/bin/env python3
"""
Script para verificar que el sistema de envío de informes esté listo
"""
import os
import sys
import django
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.models import Destinatario, Organizacion
from django.contrib.auth.models import User

def verificar_sistema():
    print("=== VERIFICACIÓN DEL SISTEMA DE ENVÍO ===\n")
    
    # 1. Verificar destinatarios
    print("📧 DESTINATARIOS:")
    destinatarios = Destinatario.objects.all()
    if destinatarios.exists():
        print(f"✅ Total destinatarios: {destinatarios.count()}")
        for d in destinatarios:
            print(f"   - {d.email} ({d.nombre}) - Org: {d.organizacion.nombre if d.organizacion else 'Sin org'}")
    else:
        print("❌ NO HAY DESTINATARIOS REGISTRADOS")
    
    print("\n🏢 ORGANIZACIONES:")
    organizaciones = Organizacion.objects.all()
    if organizaciones.exists():
        print(f"✅ Total organizaciones: {organizaciones.count()}")
        for org in organizaciones:
            print(f"   - {org.nombre} (@{org.dominio}) - Admin: {org.admin.email if org.admin else 'Sin admin'}")
    else:
        print("❌ NO HAY ORGANIZACIONES REGISTRADAS")
    
    # 2. Verificar scheduler
    print("\n⏰ SCHEDULER:")
    procfile_path = 'Procfile'
    if os.path.exists(procfile_path):
        with open(procfile_path, 'r') as f:
            content = f.read()
            if 'worker: python manage.py run_scheduler' in content:
                print("✅ Worker configurado en Procfile")
            else:
                print("❌ Worker NO configurado en Procfile")
    
    # 3. Verificar comandos
    print("\n🔧 COMANDOS DE MANAGEMENT:")
    commands_dir = 'alerts/management/commands'
    required_commands = ['run_scheduler.py', 'enviar_informes_diarios.py']
    for cmd in required_commands:
        cmd_path = os.path.join(commands_dir, cmd)
        if os.path.exists(cmd_path):
            print(f"✅ {cmd} existe")
        else:
            print(f"❌ {cmd} NO EXISTE")
    
    # 4. Verificar script generador
    print("\n📄 SCRIPT GENERADOR:")
    script_path = 'scripts/generators/generar_informe_oficial_integrado_mejorado.py'
    if os.path.exists(script_path):
        print("✅ Script generador existe")
    else:
        print("❌ Script generador NO EXISTE")
    
    # 5. Verificar variables de entorno
    print("\n🔐 VARIABLES DE ENTORNO (Heroku):")
    print("   Ejecuta: heroku config --app informediariochile")
    print("   Necesarias:")
    print("   - OPENAI_API_KEY")
    print("   - HOSTINGER_EMAIL_PASSWORD") 
    print("   - EMAIL_HOST_USER")
    print("   - EMAIL_HOST_PASSWORD")
    
    # 6. Verificar día de la semana
    print("\n📅 DÍA DE LA SEMANA:")
    hoy = datetime.now()
    dia_semana = hoy.strftime("%A")
    es_domingo = hoy.weekday() == 6
    print(f"   Hoy es: {dia_semana}")
    if es_domingo:
        print("   ⚠️ DOMINGO - No se envían informes")
    else:
        print("   ✅ Día hábil - Se enviarán informes")
    
    # 7. Resumen
    print("\n=== RESUMEN ===")
    if destinatarios.exists() and organizaciones.exists():
        print("✅ Sistema listo para enviar informes")
        print(f"   - Se enviarán a {destinatarios.count()} destinatarios")
        print("   - Hora programada: 9:00 AM")
        print("   - Próximo envío: Mañana (si es día hábil)")
    else:
        print("❌ SISTEMA NO ESTÁ LISTO")
        print("   - Registra al menos un usuario/organización")

if __name__ == "__main__":
    verificar_sistema()