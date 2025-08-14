import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

email = 'cbernales@pgb.cl'

# Buscar usuario
try:
    user = User.objects.get(email=email)
    print(f'Usuario encontrado: {user.username}')
    print(f'Nombre: {user.first_name} {user.last_name}')
    
    # Verificar si es admin
    orgs = Organizacion.objects.filter(admin=user)
    if orgs.exists():
        print(f'Ya es admin de: {orgs.first().nombre}')
    else:
        print('NO es admin - CORRIGIENDO...')
        
        # Crear organización
        org = Organizacion.objects.create(
            nombre=f'{user.first_name} {user.last_name}'.strip() or 'PGB',
            dominio='pgb.cl',
            admin=user,
            suscripcion_activa=True
        )
        print(f'Organización creada: {org.nombre}')
        
        # Crear o actualizar destinatario
        dest, created = Destinatario.objects.get_or_create(
            email=email,
            defaults={
                'nombre': f'{user.first_name} {user.last_name}'.strip() or user.username,
                'organizacion': org
            }
        )
        if not created and not dest.organizacion:
            dest.organizacion = org
            dest.save()
        print('Destinatario configurado')
        print('¡LISTO! Crescente ahora puede acceder al panel')
        
except User.DoesNotExist:
    print(f'ERROR: No existe usuario con email {email}')