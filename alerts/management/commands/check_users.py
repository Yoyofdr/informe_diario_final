from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from alerts.models import Destinatario, Organizacion

class Command(BaseCommand):
    help = 'Verifica usuarios y destinatarios en el sistema'

    def handle(self, *args, **options):
        self.stdout.write("=== VERIFICACIÓN DE USUARIOS ===")
        self.stdout.write(f"Total usuarios: {User.objects.count()}")
        self.stdout.write(f"Total destinatarios: {Destinatario.objects.count()}")
        self.stdout.write(f"Total organizaciones: {Organizacion.objects.count()}")
        
        self.stdout.write("\n=== ÚLTIMOS 5 USUARIOS ===")
        for user in User.objects.order_by('-date_joined')[:5]:
            self.stdout.write(f"- {user.email} (ID: {user.id}, creado: {user.date_joined})")
        
        self.stdout.write("\n=== ÚLTIMOS 5 DESTINATARIOS ===")
        for dest in Destinatario.objects.all()[:5]:
            self.stdout.write(f"- {dest.email} ({dest.nombre}) - Org: {dest.organizacion.nombre if dest.organizacion else 'Sin org'}")
        
        self.stdout.write("\n=== ORGANIZACIONES ===")
        for org in Organizacion.objects.all():
            self.stdout.write(f"- {org.nombre} (@{org.dominio}) - Admin: {org.admin.email if org.admin else 'Sin admin'}")
            self.stdout.write(f"  Destinatarios: {org.destinatarios.count()}")
        
        # Verificar si hay problemas
        if Destinatario.objects.count() == 0:
            self.stdout.write(self.style.ERROR("\n❌ NO HAY DESTINATARIOS - Los informes NO se enviarán"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Sistema listo - Se enviarán informes a {Destinatario.objects.count()} destinatarios"))