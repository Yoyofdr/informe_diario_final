#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el estado de usuarios y organizaciones
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario
from django.db.models import Count as ModelCount

def diagnostico_completo():
    print("="*70)
    print("DIAGNÓSTICO COMPLETO DE USUARIOS Y ORGANIZACIONES")
    print("="*70)
    
    # 1. Contar usuarios totales
    total_usuarios = User.objects.count()
    print(f"\n1. USUARIOS EN DJANGO:")
    print(f"   Total de usuarios: {total_usuarios}")
    
    # Listar primeros 10 usuarios
    print("\n   Primeros 10 usuarios:")
    for user in User.objects.all()[:10]:
        print(f"   - {user.username} | {user.email} | Admin: {user.is_superuser} | Activo: {user.is_active}")
    
    # 2. Contar organizaciones
    total_orgs = Organizacion.objects.count()
    print(f"\n2. ORGANIZACIONES:")
    print(f"   Total de organizaciones: {total_orgs}")
    
    # Listar todas las organizaciones
    print("\n   Lista de organizaciones:")
    for org in Organizacion.objects.select_related('admin').all():
        print(f"   - {org.nombre} | RUT: {org.rut} | Admin: {org.admin.email if org.admin else 'SIN ADMIN'}")
    
    # 3. Contar destinatarios
    total_dest = Destinatario.objects.count()
    print(f"\n3. DESTINATARIOS:")
    print(f"   Total de destinatarios: {total_dest}")
    
    # Agrupar destinatarios por organización
    print("\n   Destinatarios por organización:")
    for org in Organizacion.objects.annotate(num_dest=ModelCount('destinatarios')):
        print(f"   - {org.nombre}: {org.num_dest} destinatarios")
        # Mostrar primeros 5 destinatarios de cada org
        for dest in Destinatario.objects.filter(organizacion=org)[:5]:
            print(f"     • {dest.email}")
    
    # 4. Usuarios sin organización
    print(f"\n4. ANÁLISIS DE INCONSISTENCIAS:")
    
    # Usuarios que son admin pero no tienen organización
    usuarios_admin = User.objects.filter(organizaciones__isnull=False).distinct()
    print(f"   Usuarios que son admin de alguna organización: {usuarios_admin.count()}")
    
    # Usuarios que NO son admin de ninguna organización
    usuarios_sin_org = User.objects.filter(organizaciones__isnull=True)
    print(f"   Usuarios SIN organización asociada: {usuarios_sin_org.count()}")
    if usuarios_sin_org.count() > 0:
        print("   Lista de usuarios sin organización:")
        for user in usuarios_sin_org[:20]:
            print(f"     - {user.email} (username: {user.username})")
    
    # 5. Verificar si hay emails duplicados
    print(f"\n5. VERIFICACIÓN DE DUPLICADOS:")
    
    # Buscar usuarios con mismo email
    emails_duplicados = User.objects.values('email').annotate(count=ModelCount('id')).filter(count__gt=1)
    if emails_duplicados:
        print("   ⚠️ EMAILS DUPLICADOS ENCONTRADOS:")
        for dup in emails_duplicados:
            print(f"     - {dup['email']}: {dup['count']} usuarios")
            usuarios = User.objects.filter(email=dup['email'])
            for u in usuarios:
                print(f"       • ID: {u.id}, Username: {u.username}, Activo: {u.is_active}")
    else:
        print("   ✅ No hay emails duplicados")
    
    # 6. Verificar destinatarios sin usuario correspondiente
    print(f"\n6. DESTINATARIOS VS USUARIOS:")
    
    destinatarios_emails = set(Destinatario.objects.values_list('email', flat=True))
    usuarios_emails = set(User.objects.values_list('email', flat=True))
    
    # Destinatarios que NO tienen usuario
    dest_sin_usuario = destinatarios_emails - usuarios_emails
    print(f"   Destinatarios SIN usuario Django: {len(dest_sin_usuario)}")
    if dest_sin_usuario:
        print("   Primeros 10:")
        for email in list(dest_sin_usuario)[:10]:
            dest = Destinatario.objects.get(email=email)
            print(f"     - {email} (Org: {dest.organizacion.nombre})")
    
    # Usuarios que NO son destinatarios
    usuarios_sin_dest = usuarios_emails - destinatarios_emails
    print(f"   Usuarios que NO son destinatarios: {len(usuarios_sin_dest)}")
    if usuarios_sin_dest:
        print("   Primeros 10:")
        for email in list(usuarios_sin_dest)[:10]:
            print(f"     - {email}")
    
    print("\n" + "="*70)
    print("RESUMEN:")
    print(f"- Total usuarios Django: {total_usuarios}")
    print(f"- Total organizaciones: {total_orgs}")
    print(f"- Total destinatarios: {total_dest}")
    print(f"- Usuarios sin organización: {usuarios_sin_org.count()}")
    print(f"- Destinatarios sin usuario: {len(dest_sin_usuario)}")
    print("="*70)

if __name__ == "__main__":
    diagnostico_completo()