#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.models import Organizacion, Empresa, Destinatario

print("=== VERIFICACIÓN DE ORGANIZACIONES Y EMPRESAS ===")
print(f"\nTotal de organizaciones: {Organizacion.objects.count()}")
print(f"Total de empresas: {Empresa.objects.count()}")
print(f"Total de destinatarios: {Destinatario.objects.count()}")

print("\n=== ORGANIZACIONES SIN EMPRESA ASOCIADA ===")
# Verificar qué organizaciones NO tienen empresa asociada
for org in Organizacion.objects.all():
    empresa = Empresa.objects.filter(nombre__iexact=org.nombre).first()
    if not empresa:
        print(f"❌ {org.nombre} (dominio: {org.dominio}) - NO tiene empresa asociada")
        # Mostrar destinatarios que NO recibirán emails
        destinatarios = Destinatario.objects.filter(organizacion=org)
        for dest in destinatarios:
            print(f"   - {dest.email} NO recibirá informes")
    else:
        print(f"✅ {org.nombre} - Sí tiene empresa asociada: {empresa.nombre}")

print("\n=== EMPRESAS EXISTENTES ===")
for empresa in Empresa.objects.all():
    print(f"- {empresa.nombre} (ID: {empresa.id})")

print("\n🚨 PROBLEMA DETECTADO 🚨")
print("El comando informe_diario_oficial.py SOLO envía emails a organizaciones")
print("que tienen una Empresa asociada (líneas 65-67 del comando).")
print("Las organizaciones sin empresa NO reciben informes.")