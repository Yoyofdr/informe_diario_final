#!/usr/bin/env python3
"""
Script para crear un usuario de prueba y verificar que el sistema funcione
"""
import os
import sys
import django
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

def crear_usuario_prueba():
    email = "prueba@informediariochile.cl"
    
    print("=== CREANDO USUARIO DE PRUEBA ===")
    
    # Verificar si ya existe
    if User.objects.filter(email=email).exists():
        print(f"❌ Usuario {email} ya existe")
        user = User.objects.get(email=email)
    else:
        # Crear usuario
        user = User.objects.create_user(
            username=email,
            email=email,
            password="Prueba123!",
            first_name="Usuario",
            last_name="Prueba"
        )
        print(f"✅ Usuario creado: {email}")
    
    # Verificar/crear organización
    dominio = "informediariochile.cl"
    org = Organizacion.objects.filter(dominio=dominio).first()
    if not org:
        org = Organizacion.objects.create(
            nombre="Informe Diario Chile",
            dominio=dominio,
            admin=user
        )
        print(f"✅ Organización creada: {org.nombre}")
    else:
        print(f"✅ Organización existente: {org.nombre}")
    
    # Verificar/crear destinatario
    dest = Destinatario.objects.filter(email=email).first()
    if not dest:
        dest = Destinatario.objects.create(
            nombre="Usuario Prueba",
            email=email,
            organizacion=org
        )
        print(f"✅ Destinatario creado: {email}")
    else:
        print(f"✅ Destinatario existente: {email}")
    
    # Verificar totales
    print("\n=== ESTADO FINAL ===")
    print(f"Total usuarios: {User.objects.count()}")
    print(f"Total destinatarios: {Destinatario.objects.count()}")
    print(f"Total organizaciones: {Organizacion.objects.count()}")
    
    print("\n✅ Sistema listo para enviar informes")
    print(f"   Los informes se enviarán a: {email}")
    print(f"   Próximo envío: Mañana 9:00 AM (si es día hábil)")

if __name__ == "__main__":
    crear_usuario_prueba()