#!/usr/bin/env python3
"""
Script para enviar el informe de hoy de forma inmediata
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')

import django
django.setup()

from alerts.informe_diario import InformeDiario
from alerts.services.send_email import send_email

def main():
    print(f"\n🚀 ENVIANDO INFORME DEL {datetime.now().strftime('%d/%m/%Y')}")
    print("=" * 60)
    
    # Lista de destinatarios
    destinatarios = [
        'rfernandezdelrio@uc.cl',
        'rodrigo@carvuk.com',
        'conchabernardita@gmail.com',
        'bconcha1@miuandes.cl'
    ]
    
    try:
        # Generar informe
        print("📄 Generando informe...")
        informe = InformeDiario()
        html_content = informe.generar_informe(force_refresh=True)
        
        if not html_content:
            print("❌ Error: No se pudo generar el informe")
            return
            
        print("✅ Informe generado exitosamente")
        
        # Preparar asunto
        fecha_hoy = datetime.now().strftime('%d/%m/%Y')
        asunto = f"📊 Informe Diario - {fecha_hoy}"
        
        # Enviar a cada destinatario
        print(f"\n📧 Enviando a {len(destinatarios)} destinatarios...")
        enviados = 0
        fallos = 0
        
        for email in destinatarios:
            try:
                resultado = send_email(
                    to_email=email,
                    subject=asunto,
                    html_content=html_content
                )
                
                if resultado:
                    print(f"   ✅ {email}")
                    enviados += 1
                else:
                    print(f"   ❌ {email} - Error en el envío")
                    fallos += 1
                    
            except Exception as e:
                print(f"   ❌ {email} - {str(e)}")
                fallos += 1
        
        # Resumen
        print("\n" + "=" * 60)
        print(f"📊 RESUMEN:")
        print(f"   Enviados: {enviados}/{len(destinatarios)}")
        if fallos > 0:
            print(f"   Fallos: {fallos}")
        print("=" * 60)
        
        if enviados > 0:
            print("✅ Informe enviado exitosamente")
        else:
            print("❌ No se pudo enviar el informe a ningún destinatario")
            
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()