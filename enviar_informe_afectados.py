#!/usr/bin/env python3
"""
Script para enviar el informe real del 13 de agosto a los destinatarios afectados
usando el generador simplificado sin MSO
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
import django
django.setup()

from scripts.generators.generar_informe_oficial_simple import enviar_informe_oficial

# Lista de destinatarios afectados que no recibieron el informe
DESTINATARIOS_AFECTADOS = [
    "fsteinmetz@bsvv.cl",  # Ya probado exitosamente
    "lvarela@bye.cl",
    "mizcue@bye.cl", 
    "bjottar@bye.cl",
    "mulloa@bye.cl"
]

def main():
    """Enviar informe del 13 de agosto a destinatarios afectados"""
    
    print("=" * 60)
    print("REENVÍO DE INFORME A DESTINATARIOS AFECTADOS")
    print("=" * 60)
    print(f"\nDestinatarios a reenviar ({len(DESTINATARIOS_AFECTADOS)}):")
    for email in DESTINATARIOS_AFECTADOS:
        print(f"  • {email}")
    
    # Configurar destinatarios de prueba
    os.environ['INFORME_DESTINATARIOS_PRUEBA'] = ','.join(DESTINATARIOS_AFECTADOS)
    
    print("\n🔄 Enviando informe del 13 de agosto de 2025...")
    print("-" * 60)
    
    # Enviar informe del 13 de agosto
    enviar_informe_oficial("13-08-2025")
    
    print("-" * 60)
    print("\n✅ Proceso completado")
    print("\nPor favor verifica con los destinatarios que hayan recibido el informe.")

if __name__ == "__main__":
    main()