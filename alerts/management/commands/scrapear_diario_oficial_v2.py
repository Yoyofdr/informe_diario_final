from django.core.management.base import BaseCommand
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

class Command(BaseCommand):
    help = 'Versión simplificada del scraper del Diario Oficial'

    def add_arguments(self, parser):
        parser.add_argument('--fecha', type=str, help='Fecha en formato dd-mm-aaaa')

    def handle(self, *args, **options):
        fecha = options.get('fecha', datetime.now().strftime("%d-%m-%Y"))
        
        # Números de edición conocidos
        EDITIONS = {
            "11-07-2025": "44196",
            "12-07-2025": "44197",
            "10-07-2025": "44195",
        }
        
        # Obtener edición o estimar
        if fecha in EDITIONS:
            edition = EDITIONS[fecha]
        else:
            # Estimar basado en fecha base
            try:
                base_date = datetime.strptime("07-07-2025", "%d-%m-%Y")
                target_date = datetime.strptime(fecha, "%d-%m-%Y")
                days_diff = (target_date - base_date).days
                edition = str(44192 + days_diff)
            except:
                edition = ""
        
        url = f"https://www.diariooficial.interior.gob.cl/edicionelectronica/index.php?date={fecha}&edition={edition}&v=1"
        
        self.stdout.write(f"Scrapeando Diario Oficial del {fecha}")
        self.stdout.write(f"Edición: {edition}")
        self.stdout.write(f"URL: {url}")
        
        # Configurar Selenium
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        try:
            driver.get(url)
            time.sleep(5)
            
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            
            # Buscar PDFs
            pdfs = soup.find_all("a", href=lambda x: x and x.endswith(".pdf"))
            
            if not pdfs:
                self.stdout.write("No se encontraron PDFs")
                return
            
            self.stdout.write(f"\nTotal PDFs encontrados: {len(pdfs)}")
            self.stdout.write("-" * 50)
            
            # Mostrar primeros 10 PDFs
            for i, pdf in enumerate(pdfs[:10]):
                href = pdf.get('href')
                
                # Buscar título
                parent = pdf.find_parent('tr')
                titulo = "Sin título"
                if parent:
                    celdas = parent.find_all('td')
                    for celda in celdas:
                        texto = celda.get_text(strip=True)
                        if texto and not texto.startswith("Ver PDF") and len(texto) > 10:
                            titulo = texto
                            break
                
                self.stdout.write(f"\n{i+1}. {titulo}")
                self.stdout.write(f"   PDF: {href}")
                
        finally:
            driver.quit()
            
        self.stdout.write("\n✅ Scraping completado")