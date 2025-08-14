import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario

print("=" * 60)
print("BÚSQUEDA DE USUARIOS Y ORGANIZACIONES PGB.CL")
print("=" * 60)

# Buscar usuarios con dominio pgb.cl
users = User.objects.filter(email__icontains='pgb.cl')
print(f"\nUsuarios con dominio @pgb.cl: {users.count()}")
for u in users:
    print(f"  - {u.email} ({u.first_name} {u.last_name})")
    print(f"    Username: {u.username}")
    print(f"    Registrado: {u.date_joined}")

# Buscar organizaciones con dominio pgb.cl
orgs = Organizacion.objects.filter(dominio='pgb.cl')
print(f"\nOrganizaciones con dominio pgb.cl: {orgs.count()}")
for o in orgs:
    print(f"  - {o.nombre}")
    print(f"    Admin: {o.admin.email if o.admin else 'SIN ADMIN'}")

# Buscar destinatarios con email pgb.cl
dests = Destinatario.objects.filter(email__icontains='pgb.cl')
print(f"\nDestinatarios con email @pgb.cl: {dests.count()}")
for d in dests:
    print(f"  - {d.email} ({d.nombre})")
    print(f"    Org: {d.organizacion.nombre if d.organizacion else 'SIN ORG'}")

# Buscar específicamente cbernales
print("\n" + "=" * 60)
print("BÚSQUEDA ESPECÍFICA: cbernales")
print("=" * 60)

# Por email exacto
user = User.objects.filter(email='cbernales@pgb.cl').first()
if user:
    print(f"✅ Usuario encontrado: {user.username}")
else:
    print("❌ NO existe usuario con email cbernales@pgb.cl")

# Por username
user2 = User.objects.filter(username='cbernales@pgb.cl').first()
if user2:
    print(f"✅ Usuario encontrado por username: {user2.email}")
else:
    print("❌ NO existe usuario con username cbernales@pgb.cl")