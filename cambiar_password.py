#!/usr/bin/env python3
"""
Script para cambiar la contraseña de un usuario existente
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User

def cambiar_password():
    email = 'rfernandezdelrio@uc.cl'
    nueva_password = 'golden98'
    
    print(f"Cambiando contraseña para {email}...")
    
    try:
        # Buscar usuario por email
        user = User.objects.get(email=email)
        print(f"✅ Usuario encontrado: {user.username}")
        
        # Cambiar contraseña
        user.set_password(nueva_password)
        user.save()
        
        print(f"✅ Contraseña actualizada exitosamente")
        print(f"   Email: {email}")
        print(f"   Nueva contraseña: {nueva_password}")
        
        return True
        
    except User.DoesNotExist:
        print(f"❌ No existe usuario con email {email}")
        # Intentar buscar por username
        try:
            user = User.objects.get(username=email)
            print(f"✅ Usuario encontrado por username: {user.username}")
            
            # Cambiar contraseña
            user.set_password(nueva_password)
            user.save()
            
            print(f"✅ Contraseña actualizada exitosamente")
            print(f"   Username: {user.username}")
            print(f"   Nueva contraseña: {nueva_password}")
            
            return True
        except User.DoesNotExist:
            print(f"❌ No se encontró usuario con username {email}")
            return False

if __name__ == "__main__":
    if cambiar_password():
        print("\n" + "="*50)
        print("CREDENCIALES ACTUALIZADAS:")
        print("="*50)
        print(f"URL: https://informediariochile.cl/login/")
        print(f"Email: rfernandezdelrio@uc.cl")
        print(f"Contraseña: golden98")
        print("="*50)