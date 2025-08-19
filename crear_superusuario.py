#!/usr/bin/env python3
"""
Script para crear un nuevo superusuario con email
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

def crear_superusuario():
    email = 'rfernandezdelrio@uc.cl'
    username = email  # Usar el email como username para consistencia
    
    print(f"Creando superusuario para {email}...")
    
    # Verificar si ya existe
    if User.objects.filter(email=email).exists():
        print(f"❌ Ya existe un usuario con el email {email}")
        user = User.objects.get(email=email)
        if not user.is_superuser:
            print("   Actualizando a superusuario...")
            user.is_superuser = True
            user.is_staff = True
            user.save()
            print("   ✅ Usuario actualizado a superusuario")
        else:
            print("   ✅ El usuario ya es superusuario")
        return user
    
    # Crear nuevo superusuario
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password='Admin2025!',  # Contraseña temporal
            first_name='Rodrigo',
            last_name='Fernández'
        )
        
        print(f"✅ Superusuario creado exitosamente")
        print(f"   Email: {email}")
        print(f"   Contraseña: Admin2025!")
        print(f"   ⚠️ IMPORTANTE: Cambia esta contraseña después del primer login")
        
        # Opcional: Crear una organización para el admin
        if not Organizacion.objects.filter(admin=user).exists():
            org = Organizacion.objects.create(
                nombre="Administración",
                dominio="uc.cl",
                admin=user,
                tipo='independiente'
            )
            
            # Agregar como destinatario
            Destinatario.objects.create(
                nombre="Rodrigo Fernández",
                email=email,
                organizacion=org
            )
            
            print(f"✅ Organización de administración creada")
        
        return user
        
    except Exception as e:
        print(f"❌ Error creando superusuario: {e}")
        return None

if __name__ == "__main__":
    user = crear_superusuario()
    if user:
        print("\n" + "="*50)
        print("CREDENCIALES DE ACCESO:")
        print("="*50)
        print(f"URL: https://informediariochile.cl/alerts/login/")
        print(f"Email: rfernandezdelrio@uc.cl")
        print(f"Contraseña: Admin2025!")
        print("="*50)