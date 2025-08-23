"""
Descargador de PDFs usando Selenium como fallback
Para casos donde la descarga directa falla
"""
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
import os

logger = logging.getLogger(__name__)

class SeleniumPDFDownloader:
    def __init__(self):
        self.driver = None
        
    def _setup_driver(self):
        """Configura el driver de Chrome para descargas"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Configurar para manejar PDFs
        chrome_options.add_experimental_option('prefs', {
            'plugins.always_open_pdf_externally': True,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': False
        })
        
        # En Heroku usar el driver preinstalado
        if os.environ.get('DYNO'):
            chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN', '/app/.chrome-for-testing/chrome-linux64/chrome')
            service = Service(executable_path=os.environ.get('CHROMEDRIVER_PATH', '/app/.chrome-for-testing/chromedriver-linux64/chromedriver'))
        else:
            # En local usar webdriver-manager
            service = Service(ChromeDriverManager().install())
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def download_pdf_with_selenium(self, url, max_retries=3):
        """
        Descarga un PDF usando Selenium cuando falla la descarga directa
        
        Args:
            url: URL del PDF
            max_retries: Número máximo de reintentos
            
        Returns:
            bytes del PDF o None si falla
        """
        for attempt in range(max_retries):
            try:
                if not self.driver:
                    self._setup_driver()
                
                logger.info(f"🌐 Intento {attempt + 1}: Descargando PDF con Selenium")
                
                # Navegar a la URL
                self.driver.get(url)
                
                # Esperar un poco para que cargue
                time.sleep(3)
                
                # Intentar obtener el PDF de varias formas
                
                # Método 1: Si es un PDF directo, obtener desde la URL actual
                current_url = self.driver.current_url
                if current_url.endswith('.pdf') or 'application/pdf' in self.driver.execute_script("return document.contentType || ''"):
                    # Es un PDF, descargarlo directamente
                    session = requests.Session()
                    # Copiar cookies del navegador
                    for cookie in self.driver.get_cookies():
                        session.cookies.set(cookie['name'], cookie['value'])
                    
                    response = session.get(current_url, timeout=60, verify=False)
                    if response.status_code == 200 and len(response.content) > 1000:
                        logger.info(f"✅ PDF descargado con Selenium: {len(response.content)} bytes")
                        return response.content
                
                # Método 2: Buscar iframes con PDFs
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                for iframe in iframes:
                    src = iframe.get_attribute('src')
                    if src and ('.pdf' in src or 'ver_sgd.php' in src):
                        session = requests.Session()
                        for cookie in self.driver.get_cookies():
                            session.cookies.set(cookie['name'], cookie['value'])
                        
                        response = session.get(src, timeout=60, verify=False)
                        if response.status_code == 200 and len(response.content) > 1000:
                            logger.info(f"✅ PDF descargado desde iframe: {len(response.content)} bytes")
                            return response.content
                
                # Método 3: Buscar enlaces a PDFs
                pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
                if pdf_links:
                    pdf_url = pdf_links[0].get_attribute('href')
                    session = requests.Session()
                    for cookie in self.driver.get_cookies():
                        session.cookies.set(cookie['name'], cookie['value'])
                    
                    response = session.get(pdf_url, timeout=60, verify=False)
                    if response.status_code == 200 and len(response.content) > 1000:
                        logger.info(f"✅ PDF descargado desde enlace: {len(response.content)} bytes")
                        return response.content
                
                logger.warning(f"⚠️ Intento {attempt + 1} con Selenium no encontró PDF")
                
            except Exception as e:
                logger.error(f"❌ Error en intento {attempt + 1} con Selenium: {str(e)[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Esperar antes de reintentar
                    # Reiniciar driver si hay error
                    self.close()
            
        return None
    
    def close(self):
        """Cierra el driver de Selenium"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

# Instancia global (se reutiliza entre descargas)
selenium_downloader = SeleniumPDFDownloader()