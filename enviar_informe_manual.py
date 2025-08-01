#!/usr/bin/env python
"""
Script para enviar manualmente el informe a un email específico
"""
import os
import sys
import django
from datetime import datetime

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

def enviar_informe_manual():
    email = "rfernandezdelrio@uc.cl"
    fecha = datetime.now().strftime("%d-%m-%Y")
    
    print(f"=== ENVIANDO INFORME MANUAL A {email} ===")
    print(f"Fecha: {fecha}")
    
    try:
        # Importar la función de envío
        from alerts.enviar_informe_bienvenida import enviar_informe_bienvenida_simple
        
        # Enviar
        resultado = enviar_informe_bienvenida_simple(email, "Rodrigo")
        
        if resultado:
            print("\n✅ INFORME ENVIADO EXITOSAMENTE")
            print(f"Revisa tu correo: {email}")
        else:
            print("\n❌ Error enviando el informe")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        
        # Alternativa: ejecutar el comando directamente
        print("\nIntentando método alternativo...")
        from django.core.management import call_command
        
        # Temporalmente cambiar el destinatario
        os.environ['EMAIL_TO'] = email
        
        try:
            call_command('informe_diario_oficial')
            print("\n✅ Comando ejecutado")
        except Exception as e2:
            print(f"❌ Error en método alternativo: {str(e2)}")

if __name__ == "__main__":
    enviar_informe_manual()