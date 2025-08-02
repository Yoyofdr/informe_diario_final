#!/usr/bin/env python3
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario
from django.db import transaction

# Usuario de prueba con timestamp
timestamp = datetime.now().strftime('%Y%m%d%H%M')
email = f"prueba_{timestamp}@informediariochile.cl"
nombre = "Prueba"
apellido = f"Test{timestamp}"
empresa = "Test Informe Diario"
password = "Test123!"

print(f"=== CREANDO USUARIO DE PRUEBA EN PRODUCCIÓN ===")
print(f"Email: {email}")
print(f"Nombre: {nombre} {apellido}")
print(f"Empresa: {empresa}")

dominio = email.split('@')[1].lower().strip()

try:
    with transaction.atomic():
        # Crear usuario
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=nombre,
            last_name=apellido
        )
        print(f"✅ Usuario creado: ID {user.id}")
        
        # Crear organización
        org = Organizacion.objects.filter(dominio=dominio).first()
        if not org:
            org = Organizacion.objects.create(
                nombre=empresa,
                dominio=dominio,
                admin=user
            )
            print(f"✅ Organización creada: {org.nombre}")
        else:
            print(f"ℹ️ Usando organización existente: {org.nombre}")
        
        # IMPORTANTE: Crear destinatario
        destinatario = Destinatario.objects.create(
            nombre=f"{nombre} {apellido}",
            email=email,
            organizacion=org
        )
        print(f"✅ Destinatario creado: ID {destinatario.id}")
        
        # Verificar
        if not User.objects.filter(id=user.id).exists():
            raise Exception("Usuario no guardado")
        if not Destinatario.objects.filter(id=destinatario.id).exists():
            raise Exception("Destinatario no guardado")
            
    print(f"\n✅ USUARIO DE PRUEBA CREADO EXITOSAMENTE")
    print(f"✅ Este usuario RECIBIRÁ el informe diario mañana a las 9 AM")
    
    # Mostrar todos los destinatarios actuales
    print(f"\n📧 LISTA ACTUALIZADA DE DESTINATARIOS:")
    for d in Destinatario.objects.all().order_by('-id')[:5]:
        print(f"   - {d.email}")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")