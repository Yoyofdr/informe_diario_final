from django.core.management.base import BaseCommand
from alerts.scraper_diario_oficial import obtener_sumario_diario_oficial

class Command(BaseCommand):
    help = 'Scrapea el sumario del Diario Oficial de hoy o de una fecha específica y lo muestra por consola.'

    def add_arguments(self, parser):
        parser.add_argument('--fecha', type=str, help='Fecha en formato dd-mm-aaaa (opcional)')

    def handle(self, *args, **options):
        fecha = options.get('fecha')
        sumario = obtener_sumario_diario_oficial(fecha=fecha) if fecha else obtener_sumario_diario_oficial()
        publicaciones = sumario['publicaciones']
        if not publicaciones:
            self.stdout.write('No se encontró ninguna publicación para la fecha indicada.')
            return
        for entrada in publicaciones:
            self.stdout.write(f"Título: {entrada['titulo']}")
            self.stdout.write(f"PDF: {entrada['url_pdf']}")
            self.stdout.write("-") 