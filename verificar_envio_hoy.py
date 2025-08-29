#!/usr/bin/env python3
"""
Script para verificar si se envió el informe de hoy
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

from alerts.models import InformeDiario, Destinatario

# Verificar informes del 28 de agosto
fecha_hoy = datetime(2025, 8, 28)
informes = InformeDiario.objects.filter(fecha__date=fecha_hoy.date())

print(f"=== INFORMES DEL 28/08/2025 ===")
print(f"Total de informes: {informes.count()}")

if informes.exists():
    for informe in informes:
        print(f"\n📅 Informe ID: {informe.id}")
        print(f"   Fecha creación: {informe.fecha}")
        print(f"   Enviado: {'✅ SÍ' if informe.enviado else '❌ NO'}")
        if informe.contenido:
            print(f"   Contenido: {len(informe.contenido)} caracteres")
            # Ver a quiénes se debe enviar
            destinatarios = Destinatario.objects.filter(activo=True)
            print(f"   Destinatarios activos: {destinatarios.count()}")
            for dest in destinatarios:
                print(f"     - {dest.email}")
else:
    print("❌ No hay informes para el 28/08/2025")

# Verificar el último informe enviado
ultimo_enviado = InformeDiario.objects.filter(enviado=True).order_by('-fecha').first()
if ultimo_enviado:
    print(f"\n📧 ÚLTIMO INFORME ENVIADO:")
    print(f"   Fecha: {ultimo_enviado.fecha}")
    print(f"   ID: {ultimo_enviado.id}")