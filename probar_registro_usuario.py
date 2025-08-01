#!/usr/bin/env python
"""
Script para probar el flujo de registro y envío de informe de bienvenida
"""
import os
import sys
import django
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.enviar_informe_bienvenida import enviar_informe_bienvenida
from alerts.models import Destinatario, Organizacion
from django.contrib.auth.models import User

def simular_registro_usuario():
    """Simula el registro de un nuevo usuario y verifica el envío del informe"""
    
    print("=== SIMULACIÓN DE REGISTRO DE NUEVO USUARIO ===\n")
    
    # Datos de prueba
    email_prueba = "prueba@ejemplo.com"
    nombre_prueba = "Usuario Prueba"
    
    # Verificar día de la semana
    dia_semana = datetime.now().weekday()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    print(f"📅 Día actual: {dias[dia_semana]}")
    
    if dia_semana == 6:  # Domingo
        print("⚠️  Nota: Es domingo, se enviará solo correo de bienvenida sin informe\n")
    else:
        print("✅ Se enviará correo de bienvenida CON el informe del día\n")
    
    # Verificar configuración
    print("🔧 VERIFICANDO CONFIGURACIÓN:")
    
    # Email
    email_from = os.environ.get('EMAIL_HOST_USER') or "rodrigo@carvuk.com"
    email_pass = os.environ.get('EMAIL_HOST_PASSWORD') or os.environ.get('HOSTINGER_EMAIL_PASSWORD')
    print(f"   - Email remitente: {'✅' if email_from else '❌'} {email_from}")
    print(f"   - Contraseña: {'✅ Configurada' if email_pass else '❌ No configurada'}")
    
    # Script integrado
    from django.conf import settings
    possible_paths = [
        os.path.join(settings.BASE_DIR, 'repo_limpio', 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py'),
        os.path.join(settings.BASE_DIR, 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py'),
        os.path.join(settings.BASE_DIR, '..', 'repo_limpio', 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py'),
    ]
    
    script_encontrado = False
    for path in possible_paths:
        if os.path.exists(path):
            print(f"   - Script integrado: ✅ Encontrado en {path}")
            script_encontrado = True
            break
    
    if not script_encontrado:
        print("   - Script integrado: ❌ No encontrado")
    
    # Preguntar si continuar
    print(f"\n¿Deseas enviar el informe de bienvenida a {email_prueba}? (s/n): ")
    
    # Para testing automático, usar 'n'
    respuesta = 'n'
    print(f"Respuesta automática: {respuesta}")
    
    if respuesta.lower() == 's':
        print(f"\n📧 ENVIANDO INFORME DE BIENVENIDA A: {email_prueba}")
        print("=" * 50)
        
        try:
            resultado = enviar_informe_bienvenida(email_prueba, nombre_prueba)
            
            if resultado:
                print("\n✅ INFORME ENVIADO EXITOSAMENTE")
                print(f"   - Destinatario: {email_prueba}")
                print(f"   - Nombre: {nombre_prueba}")
                if dia_semana != 6:
                    print("   - Incluye: Diario Oficial + CMF + SII")
                else:
                    print("   - Solo correo de bienvenida (sin informe por ser domingo)")
            else:
                print("\n❌ ERROR AL ENVIAR EL INFORME")
                
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ Envío cancelado por el usuario")
    
    # Mostrar información adicional
    print("\n📋 INFORMACIÓN DEL FLUJO DE REGISTRO:")
    print("1. Cuando un usuario se registra en la plataforma:")
    print("   - Se crea su cuenta de usuario")
    print("   - Se crea su organización")
    print("   - Se registran los destinatarios de su empresa")
    print("   - Se envía informe de bienvenida a TODOS (admin + destinatarios)")
    print("\n2. El informe de bienvenida incluye:")
    if dia_semana != 6:
        print("   - Mensaje personalizado de bienvenida")
        print("   - Informe completo del día (Diario Oficial + CMF + SII)")
        print("   - Información sobre próximos envíos (9:00 AM diario)")
    else:
        print("   - Solo mensaje de bienvenida")
        print("   - Aviso de que recibirá el primer informe el lunes")
    
    print("\n3. A partir del día siguiente:")
    print("   - Recibirán el informe automáticamente a las 9:00 AM")
    print("   - De lunes a sábado (no domingos)")

if __name__ == "__main__":
    simular_registro_usuario()