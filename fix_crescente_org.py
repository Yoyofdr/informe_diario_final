#!/usr/bin/env python3
"""
Script para diagnosticar y corregir el problema de Crescente sin organización
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

def diagnosticar_usuario(email_o_nombre):
    """Busca y diagnostica el estado de un usuario"""
    
    print("=" * 60)
    print("DIAGNÓSTICO DE USUARIO")
    print("=" * 60)
    
    # Buscar usuario por email o nombre
    usuarios = User.objects.filter(
        email__icontains=email_o_nombre
    ) | User.objects.filter(
        first_name__icontains=email_o_nombre
    ) | User.objects.filter(
        username__icontains=email_o_nombre
    )
    
    if not usuarios.exists():
        print(f"❌ No se encontró ningún usuario con: {email_o_nombre}")
        return None
    
    for user in usuarios:
        print(f"\n📧 Usuario encontrado:")
        print(f"   - ID: {user.id}")
        print(f"   - Username: {user.username}")
        print(f"   - Email: {user.email}")
        print(f"   - Nombre: {user.first_name} {user.last_name}")
        print(f"   - Fecha registro: {user.date_joined}")
        
        # Buscar organizaciones donde es admin
        orgs_admin = Organizacion.objects.filter(admin=user)
        if orgs_admin.exists():
            print(f"\n✅ Organizaciones donde es ADMIN:")
            for org in orgs_admin:
                print(f"   - {org.nombre} (dominio: {org.dominio})")
                print(f"     ID: {org.id}")
        else:
            print(f"\n❌ NO es admin de ninguna organización")
        
        # Buscar si es destinatario
        destinatarios = Destinatario.objects.filter(email=user.email)
        if destinatarios.exists():
            print(f"\n📬 Es destinatario en:")
            for dest in destinatarios:
                print(f"   - Organización: {dest.organizacion.nombre if dest.organizacion else 'SIN ORG'}")
                print(f"     Como: {dest.nombre}")
        else:
            print(f"\n⚠️ NO está registrado como destinatario")
        
        return user
    
    return None

def crear_organizacion_para_usuario(user):
    """Crea una organización para un usuario que no tiene"""
    
    # Verificar si ya es admin de alguna org
    if Organizacion.objects.filter(admin=user).exists():
        print("⚠️ El usuario ya tiene una organización")
        return
    
    # Extraer dominio del email
    dominio = user.email.split('@')[1].lower().strip()
    
    # Verificar si ya existe una org con ese dominio
    org_existente = Organizacion.objects.filter(dominio=dominio).first()
    
    if org_existente:
        print(f"⚠️ Ya existe una organización con dominio {dominio}: {org_existente.nombre}")
        print(f"   Admin actual: {org_existente.admin.email}")
        
        respuesta = input("\n¿Quieres hacer a este usuario admin de esa organización? (s/n): ")
        if respuesta.lower() == 's':
            org_existente.admin = user
            org_existente.save()
            print(f"✅ Usuario establecido como admin de {org_existente.nombre}")
            
            # Asegurar que es destinatario también
            if not Destinatario.objects.filter(email=user.email, organizacion=org_existente).exists():
                Destinatario.objects.create(
                    nombre=f"{user.first_name} {user.last_name}".strip() or user.username,
                    email=user.email,
                    organizacion=org_existente
                )
                print(f"✅ Usuario agregado como destinatario")
        return
    
    # Crear nueva organización
    print(f"\n📝 Creando nueva organización para {user.email}")
    
    nombre_org = input(f"Nombre de la empresa/organización (Enter para usar '{dominio}'): ").strip()
    if not nombre_org:
        nombre_org = dominio.replace('.', ' ').title()
    
    org = Organizacion.objects.create(
        nombre=nombre_org,
        dominio=dominio,
        admin=user,
        suscripcion_activa=True  # Activar por defecto
    )
    
    print(f"✅ Organización creada: {org.nombre}")
    
    # Crear destinatario
    destinatario = Destinatario.objects.create(
        nombre=f"{user.first_name} {user.last_name}".strip() or user.username,
        email=user.email,
        organizacion=org
    )
    
    print(f"✅ Usuario agregado como destinatario principal")
    print(f"\n🎉 ¡Listo! El usuario ahora tiene organización y puede acceder al panel")

def main():
    print("\n🔍 DIAGNÓSTICO Y CORRECCIÓN DE USUARIOS SIN ORGANIZACIÓN\n")
    
    # Buscar directamente a Crescente
    busqueda = "crescente"
    print(f"Buscando usuario: {busqueda}")
    
    user = diagnosticar_usuario(busqueda)
    
    if not user:
        print("No se encontró el usuario")
        return
    
    # Si no tiene organización, crear una automáticamente
    if not Organizacion.objects.filter(admin=user).exists():
        print("\n" + "=" * 60)
        print("\n⚠️ El usuario NO tiene organización asociada")
        print("Creando organización automáticamente...")
        
        # Extraer dominio del email
        dominio = user.email.split('@')[1].lower().strip()
        
        # Verificar si ya existe una org con ese dominio
        org_existente = Organizacion.objects.filter(dominio=dominio).first()
        
        if org_existente:
            print(f"Ya existe una organización con dominio {dominio}: {org_existente.nombre}")
            print(f"Admin actual: {org_existente.admin.email}")
        else:
            # Crear nueva organización automáticamente
            nombre_org = dominio.replace('.', ' ').title()
            org = Organizacion.objects.create(
                nombre=nombre_org,
                dominio=dominio,
                admin=user,
                suscripcion_activa=True
            )
            print(f"✅ Organización creada: {org.nombre}")
            
            # Crear destinatario
            destinatario = Destinatario.objects.create(
                nombre=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=user.email,
                organizacion=org
            )
            print(f"✅ Usuario agregado como destinatario principal")
            print(f"\n🎉 ¡Listo! El usuario ahora tiene organización y puede acceder al panel")
    
    print("\n" + "=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)

if __name__ == "__main__":
    main()