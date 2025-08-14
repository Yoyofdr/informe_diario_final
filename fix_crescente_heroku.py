#!/usr/bin/env python3
"""
Script para diagnosticar y corregir el problema de Crescente en Heroku
"""

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

def diagnosticar_y_corregir():
    print("=" * 60)
    print("DIAGNÓSTICO DE USUARIO CRESCENTE")
    print("=" * 60)
    
    # Buscar usuario por email
    email = "cbernales@pgb.cl"
    
    try:
        user = User.objects.get(email=email)
        print(f"\n✅ Usuario encontrado:")
        print(f"   - ID: {user.id}")
        print(f"   - Username: {user.username}")
        print(f"   - Email: {user.email}")
        print(f"   - Nombre: {user.first_name} {user.last_name}")
        print(f"   - Fecha registro: {user.date_joined}")
        print(f"   - Activo: {user.is_active}")
    except User.DoesNotExist:
        print(f"❌ No se encontró usuario con email: {email}")
        return
    
    # Verificar si es admin de alguna organización
    orgs_admin = Organizacion.objects.filter(admin=user)
    if orgs_admin.exists():
        print(f"\n✅ Ya es admin de organizaciones:")
        for org in orgs_admin:
            print(f"   - {org.nombre} (dominio: {org.dominio}, ID: {org.id})")
    else:
        print(f"\n❌ NO es admin de ninguna organización")
    
    # Verificar si existe organización con dominio pgb.cl
    dominio = "pgb.cl"
    org_existente = Organizacion.objects.filter(dominio=dominio).first()
    
    if org_existente:
        print(f"\n⚠️ Ya existe organización con dominio {dominio}:")
        print(f"   - Nombre: {org_existente.nombre}")
        print(f"   - Admin actual: {org_existente.admin.email}")
        print(f"   - ID: {org_existente.id}")
    else:
        print(f"\n❌ NO existe organización con dominio {dominio}")
    
    # Verificar si es destinatario
    destinatarios = Destinatario.objects.filter(email=email)
    if destinatarios.exists():
        print(f"\n📬 Es destinatario en:")
        for dest in destinatarios:
            if dest.organizacion:
                print(f"   - Organización: {dest.organizacion.nombre}")
                print(f"     Como: {dest.nombre}")
            else:
                print(f"   - SIN ORGANIZACIÓN ASOCIADA")
    else:
        print(f"\n❌ NO está registrado como destinatario")
    
    # CORRECCIÓN AUTOMÁTICA
    print("\n" + "=" * 60)
    print("APLICANDO CORRECCIÓN")
    print("=" * 60)
    
    if not orgs_admin.exists() and not org_existente:
        # Crear la organización que falta
        print("\nCreando organización para el usuario...")
        
        # Obtener nombre de empresa del formulario (asumimos que es el nombre del usuario o dominio)
        nombre_empresa = f"{user.first_name} {user.last_name}".strip()
        if not nombre_empresa or nombre_empresa == " ":
            nombre_empresa = "PGB"  # Usar siglas del dominio
        
        org = Organizacion.objects.create(
            nombre=nombre_empresa,
            dominio=dominio,
            admin=user,
            suscripcion_activa=True
        )
        print(f"✅ Organización creada:")
        print(f"   - Nombre: {org.nombre}")
        print(f"   - Dominio: {org.dominio}")
        print(f"   - ID: {org.id}")
        
        # Verificar/crear destinatario
        if not destinatarios.exists():
            destinatario = Destinatario.objects.create(
                nombre=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=email,
                organizacion=org
            )
            print(f"\n✅ Destinatario creado:")
            print(f"   - Nombre: {destinatario.nombre}")
            print(f"   - Email: {destinatario.email}")
        else:
            # Actualizar destinatario existente
            dest = destinatarios.first()
            dest.organizacion = org
            dest.save()
            print(f"\n✅ Destinatario actualizado con organización")
        
        print(f"\n🎉 ¡CORRECCIÓN COMPLETADA!")
        print(f"El usuario {user.first_name} ahora puede acceder al panel")
    elif org_existente and not orgs_admin.exists():
        print(f"\n⚠️ Ya existe una organización con dominio {dominio}")
        print(f"No se puede hacer a {user.email} admin porque ya tiene admin: {org_existente.admin.email}")
    else:
        print("\n✅ No se requiere corrección")

if __name__ == "__main__":
    diagnosticar_y_corregir()