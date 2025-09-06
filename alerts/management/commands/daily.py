from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Alias corto para enviar_informes_diarios'

    def handle(self, *args, **options):
        # Simplemente llama al comando largo
        call_command('enviar_informes_diarios')