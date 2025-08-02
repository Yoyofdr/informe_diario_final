#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

print("=== VERIFICACIÓN DE USUARIOS Y DESTINATARIOS ===")
print(f"\nTotal de usuarios: {User.objects.count()}")
print(f"Total de organizaciones: {Organizacion.objects.count()}")
print(f"Total de destinatarios: {Destinatario.objects.count()}")

print("\n=== USUARIOS REGISTRADOS ===")
for user in User.objects.all():
    print(f"- {user.email} (ID: {user.id})")

print("\n=== ORGANIZACIONES ===")
for org in Organizacion.objects.all():
    print(f"- {org.nombre} (Dominio: {org.dominio}, Admin: {org.admin.email})")

print("\n=== DESTINATARIOS ===")
for dest in Destinatario.objects.all():
    print(f"- {dest.email} (Nombre: {dest.nombre}, Org: {dest.organizacion.nombre})")

# Verificar específicamente el usuario que intentamos crear
email_test = "rfernandezdelrio@uc.cl"
print(f"\n=== VERIFICACIÓN ESPECÍFICA: {email_test} ===")
if User.objects.filter(email=email_test).exists():
    user = User.objects.get(email=email_test)
    print(f"✅ Usuario existe: {user.email}")
    
    if Destinatario.objects.filter(email=email_test).exists():
        dest = Destinatario.objects.get(email=email_test)
        print(f"✅ Destinatario existe: {dest.email}")
        print(f"   - Organización: {dest.organizacion.nombre}")
    else:
        print("❌ Destinatario NO existe")
else:
    print("❌ Usuario NO existe")