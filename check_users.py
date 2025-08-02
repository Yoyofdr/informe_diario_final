import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Destinatario, Organizacion

print("=== VERIFICACIÓN DE USUARIOS ===")
print(f"Total usuarios: {User.objects.count()}")
print(f"Total destinatarios: {Destinatario.objects.count()}")
print(f"Total organizaciones: {Organizacion.objects.count()}")

print("\n=== ÚLTIMOS 5 USUARIOS ===")
for user in User.objects.order_by('-date_joined')[:5]:
    print(f"- {user.email} (creado: {user.date_joined})")

print("\n=== ÚLTIMOS 5 DESTINATARIOS ===")
for dest in Destinatario.objects.all()[:5]:
    print(f"- {dest.email} ({dest.nombre}) - Org: {dest.organizacion.nombre if dest.organizacion else 'Sin org'}")

print("\n=== ORGANIZACIONES ===")
for org in Organizacion.objects.all():
    print(f"- {org.nombre} (@{org.dominio}) - Admin: {org.admin.email if org.admin else 'Sin admin'}")
    print(f"  Destinatarios: {org.destinatarios.count()}")