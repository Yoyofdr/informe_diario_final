import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from alerts.models import Empresa

class Command(BaseCommand):
    help = 'Clasifica todas las empresas por rubro y si pertenecen al IPSA.'

    # La lista de IPSA se mantiene aquí como fuente principal de verdad para el índice.
    EMPRESAS_IPSA = {
        'SOC QUIMICA Y MINERA DE CHILE S.A.': 'Minería',
        'BANCO DE CHILE': 'Bancaria y Financiera',
        'BANCO SANTANDER-CHILE': 'Bancaria y Financiera',
        'EMPRESAS COPEC S.A.': 'Energía',
        'ENEL AMERICAS S.A.': 'Servicios',
        'CENCOSUD S.A.': 'Retail',
        'EMPRESAS CMPC S.A.': 'Materiales',
        'BANCO DE CREDITO E INVERSIONES': 'Bancaria y Financiera',
        'S.A.C.I. FALABELLA': 'Retail',
        'ENEL CHILE S.A.': 'Servicios',
        'PARQUE ARAUCO S.A.': 'Inmobiliario',
        'COLBUN S.A.': 'Energía',
        'COMPAÑIA CERVECERIAS UNIDAS S.A.': 'Bebestibles',
        'EMBOTELLADORA ANDINA S.A.': 'Embotelladora',
        'COMPAÑIA SUD AMERICANA DE VAPORES S.A.': 'Naviera',
        'AGUAS ANDINAS S.A.': 'Sanitaria/Agua',
        'QUINIENCO S.A.': 'Holding',
        'CENCOSUD SHOPPING S.A.': 'Inmobiliario',
        'LATAM AIRLINES GROUP S.A.': 'Aéreo',
        'VIÑA CONCHA Y TORO S.A.': 'Vitivinícola',
        'EMPRESA NACIONAL DE TELECOMUNICACIONES S.A.': 'Telecomunicaciones',
        'CAP S.A.': 'Minero-Siderúrgico',
        'NORTE GRANDE S.A.': 'Inversiones',
        'PLAZA S.A.': 'Retail',
        'ENGIE ENERGIA CHILE S.A.': 'Energía',
        'INVERSIONES AGUAS METROPOLITANAS S.A.': 'Sanitaria/Agua',
        'SMU S.A.': 'Retail',
        'ITAU CORPBANCA': 'Bancaria y Financiera',
        'SONDA S.A.': 'Tecnología',
        'RIPLEY CORP S.A.': 'Retail',
    }

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando proceso de clasificación de empresas...'))
        
        # 1. Limpieza inicial
        Empresa.objects.update(es_ipsa=False, rubro='No Clasificado')
        self.stdout.write(self.style.WARNING('Todas las empresas reseteadas a no-IPSA y "No Clasificado".'))

        # 2. Clasificar empresas IPSA desde la lista interna
        self.stdout.write(self.style.SUCCESS('\\n--- Clasificando Empresas IPSA ---'))
        ipsa_actualizadas = 0
        for nombre, rubro in self.EMPRESAS_IPSA.items():
            try:
                empresa = Empresa.objects.get(nombre__iexact=nombre)
                empresa.es_ipsa = True
                empresa.rubro = rubro
                empresa.save()
                ipsa_actualizadas += 1
                self.stdout.write(f"  - [IPSA] Actualizada: {empresa.nombre} (Rubro: {empresa.rubro})")
            except Empresa.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - [IPSA] Empresa no encontrada en DB: {nombre}"))

        self.stdout.write(self.style.SUCCESS(f'Total empresas IPSA actualizadas: {ipsa_actualizadas}'))

        # 3. Clasificar otras empresas desde el archivo CSV
        self.stdout.write(self.style.SUCCESS('\\n--- Clasificando Otras Empresas desde CSV ---'))
        csv_file_path = os.path.join(settings.BASE_DIR, 'Listado_de_Empresas_por_Rubro.csv')
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo CSV en: {csv_file_path}'))
            self.stdout.write(self.style.WARNING('Solo se clasificaron las empresas IPSA.'))
            return

        otras_actualizadas = 0
        otras_no_encontradas = []
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                nombre_empresa = row.get('Empresa')
                rubro = row.get('Rubro')

                if not nombre_empresa or not rubro:
                    self.stdout.write(self.style.WARNING(f"  - Omitiendo fila CSV por datos incompletos: {row}"))
                    continue
                
                if nombre_empresa in self.EMPRESAS_IPSA:
                    continue

                try:
                    empresa = Empresa.objects.get(nombre__iexact=nombre_empresa)
                    empresa.rubro = rubro
                    empresa.save()
                    otras_actualizadas += 1
                    self.stdout.write(f"  - [CSV] Actualizada: {empresa.nombre} (Rubro: {empresa.rubro})")
                except Empresa.DoesNotExist:
                    otras_no_encontradas.append(nombre_empresa)
        
        self.stdout.write(self.style.SUCCESS(f'Total otras empresas (desde CSV) actualizadas: {otras_actualizadas}'))
        
        if otras_no_encontradas:
            self.stdout.write(self.style.WARNING('\\nLas siguientes empresas del CSV no se encontraron en la DB:'))
            for nombre in otras_no_encontradas:
                self.stdout.write(f"  - {nombre}")

        self.stdout.write(self.style.SUCCESS('\\nProceso de clasificación finalizado.')) 