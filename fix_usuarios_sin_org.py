#!/usr/bin/env python3
"""
Script para corregir usuarios sin organización asociada
Esto no debería pasar, pero si pasa, este script lo arregla
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

def corregir_usuarios_sin_organizacion():
    print("=" * 60)
    print("VERIFICANDO USUARIOS SIN ORGANIZACIÓN")
    print("=" * 60)
    
    usuarios_sin_org = []
    
    # Buscar todos los usuarios
    for user in User.objects.all():
        # Saltar superusuarios
        if user.is_superuser:
            continue
            
        # Verificar si es admin de alguna org
        es_admin = Organizacion.objects.filter(admin=user).exists()
        
        # Verificar si es destinatario
        es_destinatario = Destinatario.objects.filter(email=user.email).exists()
        
        if not es_admin and not es_destinatario:
            usuarios_sin_org.append(user)
    
    if not usuarios_sin_org:
        print("\n✅ Todos los usuarios tienen organización asociada")
        return
    
    print(f"\n⚠️ Se encontraron {len(usuarios_sin_org)} usuarios sin organización:")
    
    for user in usuarios_sin_org:
        print(f"\n📧 Usuario: {user.email}")
        print(f"   Nombre: {user.first_name} {user.last_name}")
        print(f"   Fecha registro: {user.date_joined}")
        
        # Extraer dominio
        dominio = user.email.split('@')[1].lower().strip()
        
        # Buscar si existe org para ese dominio
        org_existente = Organizacion.objects.filter(dominio=dominio).first()
        
        if org_existente:
            print(f"   → Agregando a organización existente: {org_existente.nombre}")
            # Agregar como destinatario
            Destinatario.objects.create(
                nombre=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=user.email,
                organizacion=org_existente
            )
            print(f"   ✅ Agregado como destinatario")
        else:
            print(f"   → Creando nueva organización para dominio: {dominio}")
            # Crear nueva organización
            empresa_nombre = f"{user.first_name} {user.last_name}".strip()
            if not empresa_nombre or empresa_nombre == " ":
                # Usar el dominio como nombre de empresa
                empresa_nombre = dominio.replace('.', ' ').title()
            
            org = Organizacion.objects.create(
                nombre=empresa_nombre,
                dominio=dominio,
                admin=user,
                suscripcion_activa=True
            )
            print(f"   ✅ Organización creada: {org.nombre}")
            
            # Agregar como destinatario
            Destinatario.objects.create(
                nombre=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=user.email,
                organizacion=org
            )
            print(f"   ✅ Agregado como destinatario principal")
    
    print("\n" + "=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)

if __name__ == "__main__":
    corregir_usuarios_sin_organizacion()