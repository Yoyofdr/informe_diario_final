from django.core.management.base import BaseCommand
from alerts.models import Destinatario

class Command(BaseCommand):
    help = 'Verifica los destinatarios registrados'

    def handle(self, *args, **options):
        destinatarios = Destinatario.objects.all()
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write("DESTINATARIOS REGISTRADOS")
        self.stdout.write(f"{'='*50}")
        self.stdout.write(f"\nTotal destinatarios: {destinatarios.count()}")
        
        self.stdout.write("\nLista completa:")
        for i, dest in enumerate(destinatarios, 1):
            org = dest.organizacion.nombre if dest.organizacion else "Sin org"
            self.stdout.write(f"{i}. {dest.email} - {dest.nombre} ({org})")
        
        self.stdout.write(f"\n{'='*50}\n")