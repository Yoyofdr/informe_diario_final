#!/usr/bin/env python3
"""
Script para ver usuarios en producción
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

print('='*70)
print('USUARIOS EN PRODUCCIÓN:')
print('='*70)

# Mostrar usuarios
usuarios = User.objects.all().order_by('date_joined')
for i, user in enumerate(usuarios, 1):
    print(f'{i}. {user.email} | {user.first_name} {user.last_name} | Admin: {"SÍ" if user.is_superuser else "NO"}')

print()
print('='*70)
print(f'TOTAL: {usuarios.count()} usuarios registrados')
print('='*70)

# Mostrar organizaciones
print()
print('ORGANIZACIONES:')
print('-'*70)
orgs = Organizacion.objects.all()
for org in orgs:
    dest_count = Destinatario.objects.filter(organizacion=org).count()
    print(f'• {org.nombre} | Admin: {org.admin.email if org.admin else "SIN ADMIN"} | {dest_count} destinatarios')

print()
print('='*70)