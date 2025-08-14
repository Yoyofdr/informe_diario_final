#!/usr/bin/env python3
"""
Script para diagnosticar exactamente qué pasó con Crescente
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

def diagnosticar():
    print("=" * 60)
    print("DIAGNÓSTICO COMPLETO DE CRESCENTE")
    print("=" * 60)
    
    # 1. Buscar usuario por email
    email = 'cbernales@pgb.cl'
    try:
        user = User.objects.get(email=email)
        print(f"\n✅ Usuario encontrado:")
        print(f"   - ID: {user.id}")
        print(f"   - Username: {user.username}")
        print(f"   - Email: {user.email}")
        print(f"   - Nombre: {user.first_name} {user.last_name}")
        print(f"   - Fecha registro: {user.date_joined}")
        print(f"   - Activo: {user.is_active}")
        print(f"   - Staff: {user.is_staff}")
        print(f"   - Superuser: {user.is_superuser}")
    except User.DoesNotExist:
        print(f"❌ No existe usuario con email {email}")
        return
    
    # 2. Buscar TODAS las organizaciones con dominio pgb.cl
    print(f"\n📊 Organizaciones con dominio pgb.cl:")
    orgs_pgb = Organizacion.objects.filter(dominio='pgb.cl')
    if orgs_pgb.exists():
        for org in orgs_pgb:
            print(f"   - {org.nombre} (ID: {org.id})")
            print(f"     Admin: {org.admin.email if org.admin else 'SIN ADMIN'}")
            print(f"     Creada: {org.created_at if hasattr(org, 'created_at') else 'N/A'}")
    else:
        print("   ❌ NO existe ninguna organización con dominio pgb.cl")
    
    # 3. Buscar si Crescente es admin de ALGUNA organización
    print(f"\n📊 Organizaciones donde Crescente es admin:")
    orgs_admin = Organizacion.objects.filter(admin=user)
    if orgs_admin.exists():
        for org in orgs_admin:
            print(f"   - {org.nombre} (dominio: {org.dominio})")
    else:
        print("   ❌ NO es admin de ninguna organización")
    
    # 4. Buscar si Crescente es destinatario
    print(f"\n📊 Registros como destinatario:")
    destinatarios = Destinatario.objects.filter(email=email)
    if destinatarios.exists():
        for dest in destinatarios:
            print(f"   - ID: {dest.id}")
            print(f"     Nombre: {dest.nombre}")
            print(f"     Email: {dest.email}")
            print(f"     Organización: {dest.organizacion.nombre if dest.organizacion else 'SIN ORG'}")
            if dest.organizacion:
                print(f"     Org ID: {dest.organizacion.id}")
    else:
        print("   ❌ NO está registrado como destinatario")
    
    # 5. Buscar otros usuarios con dominio pgb.cl
    print(f"\n📊 Otros usuarios con dominio @pgb.cl:")
    otros_usuarios = User.objects.filter(email__endswith='@pgb.cl').exclude(id=user.id)
    if otros_usuarios.exists():
        for u in otros_usuarios:
            print(f"   - {u.email} (registrado: {u.date_joined})")
            es_admin = Organizacion.objects.filter(admin=u).exists()
            es_dest = Destinatario.objects.filter(email=u.email).exists()
            print(f"     Admin: {es_admin}, Destinatario: {es_dest}")
    else:
        print("   No hay otros usuarios con ese dominio")
    
    # 6. DIAGNÓSTICO
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO:")
    print("=" * 60)
    
    if not orgs_pgb.exists():
        print("❌ PROBLEMA: No existe organización para pgb.cl")
        print("   Esto NO debería pasar si Crescente fue el primer usuario")
        print("   La transacción debió haber fallado completamente")
    elif not orgs_admin.exists():
        print("❌ PROBLEMA: Crescente no es admin de ninguna org")
        print("   Pero existe org para pgb.cl")
        print("   Posible causa: Alguien más creó la org antes")
    elif not destinatarios.exists():
        print("❌ PROBLEMA: Crescente no es destinatario")
        print("   Esto es crítico - siempre debe ser destinatario")
    else:
        print("✅ Todo parece estar bien")
        print("   El problema puede estar en el dashboard")

if __name__ == "__main__":
    diagnosticar()