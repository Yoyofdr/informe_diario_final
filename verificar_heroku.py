#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.models import Destinatario, Organizacion
from django.contrib.auth.models import User

print("=== ESTADO EN HEROKU ===")
print(f"Destinatarios: {Destinatario.objects.count()}")
print(f"Organizaciones: {Organizacion.objects.count()}")
print(f"Usuarios: {User.objects.count()}")

for d in Destinatario.objects.all()[:5]:
    print(f"- {d.email}")

print("\n=== VERIFICANDO WORKER ===")
print("El worker debería estar activo en Heroku")
print("Verifica con: heroku ps --app informediariochile")