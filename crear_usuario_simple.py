#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

# Datos del usuario
email = "rfernandezdelrio@uc.cl"
password = "Test123!"
nombre = "Rodrigo"
apellido = "Fernandez"
empresa = "UC"
dominio = "uc.cl"

try:
    # Verificar si ya existe
    if User.objects.filter(email=email).exists():
        print(f"Usuario {email} ya existe")
        user = User.objects.get(email=email)
    else:
        # Crear usuario
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=nombre,
            last_name=apellido
        )
        print(f"✅ Usuario creado: {email}")
    
    # Verificar/crear organización
    org = Organizacion.objects.filter(dominio=dominio).first()
    if not org:
        org = Organizacion.objects.create(
            nombre=empresa,
            dominio=dominio,
            admin=user
        )
        print(f"✅ Organización creada: {org.nombre}")
    
    # Verificar/crear destinatario
    dest = Destinatario.objects.filter(email=email).first()
    if not dest:
        dest = Destinatario.objects.create(
            nombre=f"{nombre} {apellido}",
            email=email,
            organizacion=org
        )
        print(f"✅ Destinatario creado: {email}")
    
    print("\n✅ LISTO - Los informes se enviarán mañana a las 9 AM a:", email)
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()