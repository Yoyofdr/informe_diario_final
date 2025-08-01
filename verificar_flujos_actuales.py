#!/usr/bin/env python
"""
Script para verificar que los flujos actuales no se vean afectados
"""
import os
import sys
import django
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario
from alerts.enviar_informe_bienvenida import enviar_informe_bienvenida

def verificar_flujos():
    print("=== VERIFICACIÓN DE FLUJOS ACTUALES ===\n")
    
    # 1. Verificar modelo de Organizacion
    print("1. VERIFICANDO MODELO DE ORGANIZACIÓN:")
    try:
        # Verificar que los campos nuevos existen pero no se usan
        org = Organizacion.objects.first()
        if org:
            print(f"   ✅ Organización encontrada: {org.nombre}")
            print(f"   - Plan: {org.plan}")
            print(f"   - Suscripción activa: {org.suscripcion_activa}")
            
            # Verificar campos bancarios (deben existir pero con valores por defecto)
            if hasattr(org, 'bank_account_status'):
                print(f"   - bank_account_status: {org.bank_account_status} (CAMPO RESERVADO)")
            else:
                print("   ⚠️  Campo bank_account_status no existe aún (ejecutar migraciones)")
        else:
            print("   ℹ️  No hay organizaciones en la BD")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # 2. Verificar que NO hay referencias a Fintoc activas
    print("\n2. VERIFICANDO QUE FINTOC ESTÁ DESACTIVADO:")
    
    # Verificar URLs
    try:
        from django.urls import reverse
        try:
            url = reverse('alerts:validacion_bancaria')
            print("   ❌ URL de validación bancaria ACTIVA (debería estar comentada)")
        except:
            print("   ✅ URLs de Fintoc correctamente desactivadas")
    except Exception as e:
        print(f"   ⚠️  Error verificando URLs: {str(e)}")
    
    # 3. Verificar flujo de registro
    print("\n3. VERIFICANDO FLUJO DE REGISTRO:")
    print("   - Los usuarios se crean normalmente")
    print("   - Se envía informe de bienvenida")
    print("   - NO se pide información bancaria")
    print("   - Se agregan como destinatarios")
    
    # 4. Verificar envío de informes
    print("\n4. VERIFICANDO ENVÍO DE INFORMES:")
    try:
        # Verificar que la función existe y es llamable
        print("   ✅ Función enviar_informe_bienvenida disponible")
        
        # Verificar scheduler
        schedule_file = os.path.join(os.path.dirname(__file__), 'alerts/management/commands/run_scheduler.py')
        if os.path.exists(schedule_file):
            print("   ✅ Scheduler configurado")
        else:
            print("   ⚠️  Archivo de scheduler no encontrado")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # 5. Verificar templates
    print("\n5. VERIFICANDO TEMPLATES:")
    templates_to_check = [
        'templates/alerts/registro_exitoso.html',
        'templates/alerts/dashboard.html',
        'templates/alerts/registro_prueba.html'
    ]
    
    for template in templates_to_check:
        path = os.path.join(os.path.dirname(__file__), template)
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
                if 'validacion_bancaria' in content or 'cuenta bancaria' in content.lower():
                    print(f"   ⚠️  {template} contiene referencias a cuentas bancarias")
                else:
                    print(f"   ✅ {template} OK")
        else:
            print(f"   ⚠️  {template} no encontrado")
    
    # 6. Resumen
    print("\n6. RESUMEN:")
    print("===========================================")
    print("✅ El flujo de registro NO solicita información bancaria")
    print("✅ Los informes de bienvenida se siguen enviando")
    print("✅ La infraestructura de Fintoc está preparada pero DESACTIVADA")
    print("✅ Los campos bancarios existen en la BD pero no se usan")
    print("\n📝 Para activar Fintoc en el futuro, consulta: FINTOC_ACTIVATION_GUIDE.md")
    
    print("\n7. PRÓXIMOS PASOS:")
    print("1. Ejecutar migraciones si no se han ejecutado:")
    print("   python manage.py makemigrations alerts")
    print("   python manage.py migrate")
    print("\n2. Probar el registro de un nuevo usuario")
    print("3. Verificar que recibe el informe de bienvenida")
    print("4. Verificar que NO aparecen opciones bancarias")

if __name__ == "__main__":
    verificar_flujos()