import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from django.contrib.auth import get_user_model
from alerts.models import Organizacion

User = get_user_model()

# Crear usuario de prueba
email = "test@example.com"
password = "test123"

if not User.objects.filter(email=email).exists():
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name="Usuario",
        last_name="Prueba"
    )
    
    # Crear organización de prueba
    org = Organizacion.objects.create(
        nombre="Empresa Demo",
        dominio="example.com",
        admin=user
    )
    user.organizacion = org
    user.save()
    
    print(f"✅ Usuario creado exitosamente:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   Organización: {org.nombre}")
else:
    print(f"ℹ️ El usuario {email} ya existe")
    
print("\n🌐 Ahora puedes hacer login en: http://localhost:8001/login/")