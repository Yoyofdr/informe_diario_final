import pandas as pd
from django.core.management.base import BaseCommand
from alerts.models import Empresa

class Command(BaseCommand):
    help = 'Importa empresas desde un archivo Excel a la base de datos'

    def handle(self, *args, **options):
        archivo_excel = 'hechos_esenciales.xlsx'
        self.stdout.write(self.style.NOTICE(f"Iniciando importación desde '{archivo_excel}'..."))

        try:
            df = pd.read_excel(archivo_excel, engine='openpyxl')
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Error: No se encontró el archivo '{archivo_excel}' en el directorio raíz."))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al leer el archivo Excel: {e}"))
            return

        if 'Entidad' not in df.columns:
            self.stderr.write(self.style.ERROR("Error: La columna 'Entidad' no se encuentra en el archivo Excel."))
            return

        empresas_creadas = 0
        empresas_existentes = 0
        
        entidades_unicas = df['Entidad'].dropna().unique()

        for nombre_entidad in entidades_unicas:
            _, created = Empresa.objects.get_or_create(nombre=str(nombre_entidad).strip())
            if created:
                empresas_creadas += 1
            else:
                empresas_existentes += 1
        
        self.stdout.write(self.style.SUCCESS(f"¡Proceso completado!"))
        self.stdout.write(f"- {empresas_creadas} empresas nuevas fueron añadidas a la base de datos.")
        self.stdout.write(f"- {empresas_existentes} empresas ya existían y no fueron modificadas.") 