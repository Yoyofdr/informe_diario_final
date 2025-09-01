#!/usr/bin/env python3
"""
SOLUCIÓN DEFINITIVA PARA PDFs DE CMF
Maneja las URLs especiales con tokens de CMF
"""

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import base64
from io import BytesIO
import PyPDF2
from pdfminer.high_level import extract_text as pdfminer_extract
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtractorCMFDefinitivo:
    """Extractor definitivo para PDFs de CMF con URLs de token"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,text/html,application/xhtml+xml,*/*',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Referer': 'https://www.cmfchile.cl/'
        })
    
    def descargar_pdf_cmf(self, url_token):
        """
        Descarga PDF de CMF manejando URLs con token
        Las URLs de CMF tienen formato:
        https://www.cmfchile.cl/sitio/aplic/serdoc/ver_sgd.php?s567=XXX&secuencia=-1&t=YYY
        """
        logger.info(f"Descargando PDF de CMF: {url_token[:80]}...")
        
        # Método 1: Descarga directa con cookies de sesión
        try:
            # Primero obtener cookies visitando la página principal
            self.session.get('https://www.cmfchile.cl/', timeout=10, verify=False)
            
            # Ahora intentar descargar el PDF
            response = self.session.get(url_token, timeout=60, verify=False, allow_redirects=True)
            
            if response.status_code == 200:
                content = response.content
                
                # Verificar si es HTML (redirección) o PDF real
                if content[:4] == b'%PDF':
                    logger.info(f"✅ PDF descargado: {len(content)} bytes")
                    return content
                elif b'<html' in content[:500].lower():
                    logger.warning("Respuesta es HTML, no PDF. Intentando método 2...")
                else:
                    logger.warning(f"Contenido desconocido. Primeros bytes: {content[:20]}")
                    
        except Exception as e:
            logger.error(f"Método 1 falló: {e}")
        
        # Método 2: Usar Selenium para manejar JavaScript/redirecciones
        try:
            logger.info("Intentando con Selenium...")
            return self.descargar_con_selenium(url_token)
        except Exception as e:
            logger.error(f"Selenium también falló: {e}")
        
        # Método 3: Extraer información directamente del sitio CMF
        try:
            logger.info("Intentando scraping directo del sitio CMF...")
            return self.scraping_directo_cmf(url_token)
        except Exception as e:
            logger.error(f"Scraping directo falló: {e}")
        
        return None
    
    def descargar_con_selenium(self, url):
        """Descarga usando Selenium para manejar JavaScript"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Configurar para descargar PDFs
        prefs = {
            "download.default_directory": "/tmp",
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_settings.popups": 0,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Navegar a la URL
            driver.get(url)
            
            # Esperar un poco para que cargue
            time.sleep(5)
            
            # Verificar si hay un iframe con el PDF
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                # Cambiar al iframe
                driver.switch_to.frame(iframes[0])
                time.sleep(2)
            
            # Intentar obtener el PDF via JavaScript
            pdf_data = driver.execute_script("""
                var xhr = new XMLHttpRequest();
                xhr.open('GET', arguments[0], false);
                xhr.responseType = 'arraybuffer';
                xhr.send();
                
                var uInt8Array = new Uint8Array(xhr.response);
                var array = [];
                for (var i = 0; i < uInt8Array.length; i++) {
                    array.push(uInt8Array[i]);
                }
                return array;
            """, url)
            
            if pdf_data:
                pdf_bytes = bytes(pdf_data)
                if pdf_bytes[:4] == b'%PDF':
                    logger.info(f"✅ PDF obtenido con Selenium: {len(pdf_bytes)} bytes")
                    return pdf_bytes
                    
        except Exception as e:
            logger.error(f"Error en Selenium: {e}")
        finally:
            driver.quit()
        
        return None
    
    def scraping_directo_cmf(self, url):
        """Extrae información directamente del HTML de CMF"""
        # Este método extraería el texto directamente del HTML
        # sin necesidad del PDF
        try:
            response = self.session.get(url, timeout=30, verify=False)
            if response.status_code == 200:
                html = response.text
                
                # Buscar el contenido del hecho esencial en el HTML
                # CMF a veces muestra el contenido directamente
                if 'class="contenido"' in html or 'id="contenido"' in html:
                    # Extraer texto del HTML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Buscar divs con contenido
                    contenido = soup.find_all(['div', 'p'], class_=['contenido', 'texto', 'content'])
                    if contenido:
                        texto = ' '.join([c.get_text() for c in contenido])
                        if len(texto) > 100:
                            logger.info(f"✅ Texto extraído del HTML: {len(texto)} caracteres")
                            # Simular un PDF con el texto
                            return self.crear_pdf_desde_texto(texto)
        except Exception as e:
            logger.error(f"Error en scraping directo: {e}")
        
        return None
    
    def crear_pdf_desde_texto(self, texto):
        """Crea un PDF simple desde texto extraído"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Escribir texto en el PDF
        y = 750
        for line in texto.split('\n')[:50]:  # Primeras 50 líneas
            c.drawString(50, y, line[:100])  # Máximo 100 caracteres por línea
            y -= 15
            if y < 50:
                c.showPage()
                y = 750
        
        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def extraer_texto_garantizado(self, pdf_content):
        """Extrae texto del PDF usando múltiples métodos"""
        if not pdf_content:
            return ""
        
        texto = ""
        
        # Método 1: PyPDF2
        try:
            with BytesIO(pdf_content) as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages:
                    texto += page.extract_text() + "\n"
            
            if len(texto.strip()) > 50:
                return texto.strip()
        except:
            pass
        
        # Método 2: pdfminer
        try:
            with BytesIO(pdf_content) as pdf_file:
                texto = pdfminer_extract(pdf_file)
            
            if len(texto.strip()) > 50:
                return texto.strip()
        except:
            pass
        
        # Método 3: Fuerza bruta
        try:
            texto_raw = pdf_content.decode('latin-1', errors='ignore')
            import re
            # Buscar texto entre paréntesis (común en PDFs)
            matches = re.findall(r'\((.*?)\)', texto_raw)
            texto = ' '.join(matches)
            
            if len(texto.strip()) > 50:
                return texto.strip()
        except:
            pass
        
        return texto

def procesar_hecho_cmf_definitivo(hecho):
    """
    Procesa un hecho CMF con la solución definitiva
    """
    entidad = hecho.get('entidad', '')
    materia = hecho.get('materia', '')
    url_pdf = hecho.get('url_pdf', '')
    
    if not url_pdf:
        # Si no hay URL, usar la información disponible
        if materia and entidad:
            return f"{entidad}: {materia}. Información adicional disponible en el sitio web de CMF."
        return None
    
    # Usar el extractor definitivo
    extractor = ExtractorCMFDefinitivo()
    
    # Descargar PDF
    pdf_content = extractor.descargar_pdf_cmf(url_pdf)
    
    if pdf_content:
        # Extraer texto
        texto = extractor.extraer_texto_garantizado(pdf_content)
        
        if texto:
            # Generar resumen (aquí iría la llamada a OpenAI)
            resumen = f"{entidad}: {materia}. {texto[:200]}..."
            return resumen
    
    # Si todo falla, al menos devolver la información básica
    return f"{entidad}: {materia}. Para más detalles, consultar el sitio web de CMF."

# Código mejorado para el generador
CODIGO_MEJORADO = '''
# En generar_informe_oficial_integrado_mejorado.py

def procesar_hecho_cmf(hecho):
    """Procesa un hecho CMF con manejo especial de URLs con token"""
    entidad = hecho.get('entidad', '')
    materia = hecho.get('materia', hecho.get('titulo', ''))
    url_pdf = hecho.get('url_pdf', '')
    
    # IMPORTANTE: Las URLs de CMF tienen tokens de sesión
    # Formato: https://www.cmfchile.cl/sitio/aplic/serdoc/ver_sgd.php?s567=XXX&secuencia=-1&t=YYY
    
    if not url_pdf:
        # Si no hay URL, usar información disponible
        if materia and entidad:
            hecho['resumen'] = f"{entidad}: {materia}. Información disponible en CMF."
            return hecho
        return None
    
    # Configurar sesión con cookies
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf,text/html,*/*',
        'Accept-Language': 'es-ES,es;q=0.9',
        'Referer': 'https://www.cmfchile.cl/institucional/hechos/hechos_portada.php',
        'Cookie': 'PHPSESSID=dummy; path=/; domain=.cmfchile.cl'  # Cookie dummy para sesión
    })
    
    pdf_content = None
    
    # Intentar obtener el PDF
    try:
        # Primero, establecer sesión visitando la página principal
        session.get('https://www.cmfchile.cl/', timeout=10, verify=False)
        
        # Ahora intentar descargar el PDF con la sesión establecida
        response = session.get(url_pdf, timeout=120, verify=False, allow_redirects=True, stream=True)
        
        if response.status_code == 200:
            content = response.content
            
            # Verificar si es PDF o HTML
            if content[:4] == b'%PDF':
                pdf_content = content
                logger.info(f"✅ PDF descargado para {entidad}: {len(pdf_content)} bytes")
            elif b'<html' in content[:1000].lower():
                # Es HTML, intentar extraer información del HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # Buscar texto relevante en el HTML
                texto_elementos = soup.find_all(['p', 'div'], text=True)
                texto = ' '.join([elem.get_text() for elem in texto_elementos])
                
                if len(texto) > 100:
                    hecho['resumen'] = f"{entidad}: {materia}. {texto[:300]}..."
                    return hecho
    except Exception as e:
        logger.error(f"Error descargando PDF de {entidad}: {e}")
    
    # Si no pudimos obtener el PDF, intentar con Selenium
    if not pdf_content:
        try:
            pdf_content = selenium_downloader.download_pdf_with_selenium(url_pdf)
        except:
            pass
    
    # Extraer texto si tenemos PDF
    if pdf_content:
        try:
            texto_extraido, metodo = pdf_extractor.extract_text(pdf_content, max_pages=15)
            if texto_extraido and len(texto_extraido) > 50:
                # Generar resumen con IA
                resumen = generar_resumen_cmf(entidad, materia, texto_extraido)
                if resumen:
                    hecho['resumen'] = resumen
                    return hecho
        except Exception as e:
            logger.error(f"Error extrayendo texto de {entidad}: {e}")
    
    # Último recurso: usar información básica disponible
    hecho['resumen'] = f"{entidad}: {materia}. Documento disponible en el sitio web de CMF."
    return hecho
'''

if __name__ == "__main__":
    print("🚀 SOLUCIÓN DEFINITIVA PARA PDFs DE CMF")
    print("=" * 60)
    print()
    print("PROBLEMA IDENTIFICADO:")
    print("- Las URLs de CMF usan tokens de sesión")
    print("- Formato: ver_sgd.php?s567=TOKEN&secuencia=-1&t=TIMESTAMP")
    print("- Requieren cookies de sesión para descargar")
    print()
    print("SOLUCIÓN IMPLEMENTADA:")
    print("1. Establecer sesión con cookies antes de descargar")
    print("2. Si falla, usar Selenium con manejo de JavaScript")
    print("3. Si es HTML, extraer texto directamente del HTML")
    print("4. Siempre devolver al menos información básica")
    print()
    print("CÓDIGO MEJORADO DISPONIBLE ARRIBA ☝️")