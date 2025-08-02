#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

email = "rfernandezdelrio@uc.cl"

# Verificar que el usuario existe
if User.objects.filter(email=email).exists():
    user = User.objects.get(email=email)
    print(f"✅ Usuario encontrado: {user.email}")
    
    # Buscar o crear organización para UC
    org, created = Organizacion.objects.get_or_create(
        dominio="uc.cl",
        defaults={
            'nombre': 'Universidad Católica',
            'admin': user
        }
    )
    
    if created:
        print(f"✅ Organización creada: {org.nombre}")
    else:
        print(f"✅ Organización existente: {org.nombre}")
    
    # Crear destinatario
    dest, created = Destinatario.objects.get_or_create(
        email=email,
        defaults={
            'nombre': 'Rodrigo Fernández del Río',
            'organizacion': org
        }
    )
    
    if created:
        print(f"✅ Destinatario creado: {dest.email}")
        print(f"   - Nombre: {dest.nombre}")
        print(f"   - Organización: {dest.organizacion.nombre}")
    else:
        print(f"✅ Destinatario ya existía: {dest.email}")
    
    print(f"\n✅ Total destinatarios actualmente: {Destinatario.objects.count()}")
    
else:
    print(f"❌ Usuario NO encontrado: {email}")
    print("   Primero debes crear el usuario antes de poder crear el destinatario")