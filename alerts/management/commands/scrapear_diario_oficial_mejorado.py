from django.core.management.base import BaseCommand
from django.utils import timezone
from alerts.models import DiarioOficialScraping
from alerts.scraper_diario_oficial_mejorado import obtener_sumario_diario_oficial
from datetime import datetime
import json

class Command(BaseCommand):
    help = 'Scrapea el Diario Oficial para una fecha específica (versión mejorada)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha en formato dd-mm-aaaa',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización ignorando caché',
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Mostrar información detallada de debug',
        )

    def handle(self, *args, **options):
        fecha_str = options['fecha']
        force_refresh = options['force']
        debug = options['debug']
        
        if not fecha_str:
            fecha_str = datetime.now().strftime('%d-%m-%Y')
        
        self.stdout.write(f'Scrapeando Diario Oficial para fecha: {fecha_str}')
        if force_refresh:
            self.stdout.write('Forzando actualización (ignorando caché)')
        
        try:
            # Ejecutar scraping
            resultado = obtener_sumario_diario_oficial(fecha=fecha_str, force_refresh=force_refresh)
            
            if not resultado or not isinstance(resultado, dict):
                self.stdout.write(self.style.ERROR('Error: No se obtuvo resultado del scraping'))
                return
            
            publicaciones = resultado.get('publicaciones', [])
            valores_monedas = resultado.get('valores_monedas', {})
            total_documentos = resultado.get('total_documentos', 0)
            
            # Mostrar resumen
            self.stdout.write(f'\nTotal documentos en el Diario: {total_documentos}')
            self.stdout.write(f'Publicaciones relevantes encontradas: {len(publicaciones)}')
            
            # Contar licitaciones
            licitaciones = [p for p in publicaciones if p.get('es_licitacion', False) or 
                          any(kw in p['titulo'].lower() for kw in ['licitación', 'bases de licitación', 'concurso público'])]
            
            if licitaciones:
                self.stdout.write(self.style.SUCCESS(f'\n¡LICITACIONES ENCONTRADAS: {len(licitaciones)}!'))
                for lic in licitaciones:
                    self.stdout.write(f"  - {lic['titulo']}")
            else:
                self.stdout.write(self.style.WARNING('\nNo se encontraron licitaciones'))
            
            # Mostrar valores de monedas si existen
            if valores_monedas:
                dolar = valores_monedas.get('dolar')
                euro = valores_monedas.get('euro')
                if dolar or euro:
                    self.stdout.write('\nValores de monedas:')
                    if dolar:
                        self.stdout.write(f'  Dólar: ${dolar}')
                    if euro:
                        self.stdout.write(f'  Euro: ${euro}')
            
            # Guardar en base de datos
            fecha_dt = datetime.strptime(fecha_str, '%d-%m-%Y')
            fecha_dt = timezone.make_aware(fecha_dt.replace(hour=0, minute=0, second=0))
            
            scraping, created = DiarioOficialScraping.objects.update_or_create(
                fecha=fecha_dt.date(),
                defaults={
                    'contenido': json.dumps(resultado, ensure_ascii=False),
                    'ultima_actualizacion': timezone.now()
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Nuevo registro creado para {fecha_str}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Registro actualizado para {fecha_str}'))
            
            # Modo debug: mostrar todas las publicaciones
            if debug:
                self.stdout.write('\n--- DETALLE DE PUBLICACIONES ---')
                for i, pub in enumerate(publicaciones, 1):
                    self.stdout.write(f'\n{i}. {pub["titulo"]}')
                    self.stdout.write(f'   Sección: {pub["seccion"]}')
                    self.stdout.write(f'   Relevante: {pub["relevante"]}')
                    self.stdout.write(f'   Es licitación: {pub.get("es_licitacion", False)}')
                    self.stdout.write(f'   URL: {pub["url_pdf"]}')
                    if pub.get('resumen'):
                        self.stdout.write(f'   Resumen: {pub["resumen"][:200]}...')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error durante el scraping: {str(e)}'))
            import traceback
            traceback.print_exc()