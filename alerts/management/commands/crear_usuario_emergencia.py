from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from alerts.models import Organizacion, Destinatario
from django.db import transaction

class Command(BaseCommand):
    help = 'Crea un usuario de emergencia para asegurar que haya destinatarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='rfernandezdelrio@uc.cl',
            help='Email del usuario a crear'
        )
    
    def handle(self, *args, **options):
        email = options['email']
        
        try:
            with transaction.atomic():
                # Verificar si ya existe
                if User.objects.filter(email=email).exists():
                    self.stdout.write(f"Usuario {email} ya existe")
                    user = User.objects.get(email=email)
                else:
                    # Crear usuario
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password="InformeDiario2025!",
                        first_name="Usuario",
                        last_name="Emergencia"
                    )
                    self.stdout.write(self.style.SUCCESS(f"✅ Usuario creado: {email}"))
                
                # Crear/verificar organización
                dominio = email.split('@')[1]
                org = Organizacion.objects.filter(dominio=dominio).first()
                if not org:
                    org = Organizacion.objects.create(
                        nombre=f"Organización {dominio}",
                        dominio=dominio,
                        admin=user
                    )
                    self.stdout.write(self.style.SUCCESS(f"✅ Organización creada: {org.nombre}"))
                
                # Crear/verificar destinatario
                dest = Destinatario.objects.filter(email=email).first()
                if not dest:
                    dest = Destinatario.objects.create(
                        nombre="Usuario Emergencia",
                        email=email,
                        organizacion=org
                    )
                    self.stdout.write(self.style.SUCCESS(f"✅ Destinatario creado: {email}"))
                
                # Mostrar estado
                total_dest = Destinatario.objects.count()
                self.stdout.write(self.style.SUCCESS(f"\n✅ SISTEMA LISTO - {total_dest} destinatarios totales"))
                self.stdout.write(f"Los informes se enviarán mañana a las 9:00 AM")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))