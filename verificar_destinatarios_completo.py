#!/usr/bin/env python
"""
Script para verificar TODOS los destinatarios y usuarios registrados
"""
import os
import sys
import django
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.models import Destinatario, Organizacion, InformeEnviado
from django.contrib.auth.models import User

def main():
    print("=== VERIFICACIÓN COMPLETA DE USUARIOS Y DESTINATARIOS ===\n")
    
    # 1. Usuarios registrados
    print("1. USUARIOS REGISTRADOS EN EL SISTEMA:")
    usuarios = User.objects.all().order_by('-date_joined')
    if usuarios:
        print(f"   Total: {usuarios.count()} usuarios\n")
        for user in usuarios:
            print(f"   👤 {user.username}")
            print(f"      Email: {user.email}")
            print(f"      Nombre: {user.first_name} {user.last_name}")
            print(f"      Registrado: {user.date_joined.strftime('%d/%m/%Y %H:%M')}")
            print(f"      Activo: {'✅' if user.is_active else '❌'}")
            print(f"      Admin: {'Sí' if user.is_superuser else 'No'}")
            
            # Verificar si tiene organización
            try:
                org = Organizacion.objects.get(admin=user)
                print(f"      Organización: {org.nombre}")
            except Organizacion.DoesNotExist:
                print(f"      Organización: ❌ No tiene")
            print()
    else:
        print("   ❌ No hay usuarios registrados\n")
    
    # 2. Organizaciones
    print("\n2. ORGANIZACIONES REGISTRADAS:")
    organizaciones = Organizacion.objects.all()
    if organizaciones:
        print(f"   Total: {organizaciones.count()} organizaciones\n")
        for org in organizaciones:
            print(f"   🏢 {org.nombre}")
            print(f"      Dominio: {org.dominio}")
            print(f"      Admin: {org.admin.email if org.admin else 'Sin admin'}")
            print(f"      Creada: {org.creado.strftime('%d/%m/%Y %H:%M')}")
            print()
    else:
        print("   ❌ No hay organizaciones registradas\n")
    
    # 3. Destinatarios
    print("\n3. TODOS LOS DESTINATARIOS:")
    destinatarios = Destinatario.objects.select_related('organizacion').all()
    if destinatarios:
        print(f"   Total: {destinatarios.count()} destinatarios\n")
        for dest in destinatarios:
            print(f"   ✉️  {dest.email}")
            print(f"      Nombre: {dest.nombre}")
            print(f"      Organización: {dest.organizacion.nombre if dest.organizacion else 'Sin organización'}")
            print(f"      Creado: {dest.creado.strftime('%d/%m/%Y %H:%M')}")
            print()
    else:
        print("   ❌ No hay destinatarios registrados\n")
    
    # 4. Buscar registros recientes (últimos 7 días)
    print("\n4. REGISTROS RECIENTES (últimos 7 días):")
    fecha_limite = datetime.now() - timedelta(days=7)
    
    usuarios_recientes = User.objects.filter(date_joined__gte=fecha_limite).order_by('-date_joined')
    if usuarios_recientes:
        print(f"   Usuarios nuevos: {usuarios_recientes.count()}")
        for user in usuarios_recientes:
            print(f"   - {user.email} ({user.date_joined.strftime('%d/%m %H:%M')})")
    else:
        print("   No hay usuarios nuevos")
    
    dest_recientes = Destinatario.objects.filter(creado__gte=fecha_limite).order_by('-creado')
    if dest_recientes:
        print(f"\n   Destinatarios nuevos: {dest_recientes.count()}")
        for dest in dest_recientes:
            print(f"   - {dest.email} ({dest.creado.strftime('%d/%m %H:%M')})")
    else:
        print("\n   No hay destinatarios nuevos")
    
    # 5. Verificar envíos de bienvenida recientes
    print("\n\n5. ÚLTIMOS INFORMES ENVIADOS:")
    informes_recientes = InformeEnviado.objects.order_by('-fecha_envio')[:10]
    if informes_recientes:
        for informe in informes_recientes:
            print(f"   📧 {informe.fecha_envio.strftime('%d/%m/%Y %H:%M')}")
            print(f"      Para: {informe.destinatarios}")
            if informe.empresa:
                print(f"      Empresa: {informe.empresa.nombre}")
            print()
    else:
        print("   No hay registros de envíos")
    
    # 6. Buscar problemas potenciales
    print("\n6. VERIFICACIÓN DE PROBLEMAS:")
    
    # Usuarios sin organización
    usuarios_sin_org = []
    for user in usuarios:
        if not user.is_superuser:
            try:
                Organizacion.objects.get(admin=user)
            except Organizacion.DoesNotExist:
                usuarios_sin_org.append(user)
    
    if usuarios_sin_org:
        print("   ⚠️  Usuarios sin organización:")
        for user in usuarios_sin_org:
            print(f"      - {user.email}")
    else:
        print("   ✅ Todos los usuarios tienen organización")
    
    # Organizaciones sin destinatarios
    orgs_sin_dest = []
    for org in organizaciones:
        if not Destinatario.objects.filter(organizacion=org).exists():
            orgs_sin_dest.append(org)
    
    if orgs_sin_dest:
        print("\n   ⚠️  Organizaciones sin destinatarios:")
        for org in orgs_sin_dest:
            print(f"      - {org.nombre}")
    else:
        print("\n   ✅ Todas las organizaciones tienen destinatarios")
    
    print("\n" + "="*60)
    print("Verificación completada")

if __name__ == "__main__":
    main()