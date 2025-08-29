#!/usr/bin/env python3
"""
Scraper para obtener reglamentos de la Contraloría General de la República
https://www.contraloria.cl/web/cgr/tramitacion-de-reglamentos1
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperContraloriaReglamentos:
    def __init__(self):
        self.base_url = "https://www.contraloria.cl"
        self.reglamentos_url = "https://www.contraloria.cl/web/cgr/tramitacion-de-reglamentos1"
        
    def _setup_driver(self):
        """Configura el driver de Chrome para scraping"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    
    def obtener_reglamentos_dia_anterior(self) -> List[Dict]:
        """
        Obtiene los reglamentos publicados el día anterior
        """
        fecha_ayer = datetime.now() - timedelta(days=1)
        return self.obtener_reglamentos_por_fecha(fecha_ayer)
    
    def obtener_reglamentos_por_fecha(self, fecha: datetime) -> List[Dict]:
        """
        Obtiene los reglamentos de una fecha específica
        """
        fecha_str = fecha.strftime('%d/%m/%Y')
        logger.info(f"Buscando reglamentos del {fecha_str}")
        
        driver = None
        try:
            driver = self._setup_driver()
            driver.get(self.reglamentos_url)
            
            # Esperar a que la tabla cargue
            wait = WebDriverWait(driver, 20)
            tabla = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table, .table, [class*='table']")))
            
            time.sleep(3)  # Dar tiempo adicional para que cargue JavaScript
            
            # Obtener el HTML actual
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Buscar la tabla de reglamentos
            reglamentos = self._extraer_reglamentos_tabla(soup, fecha)
            
            logger.info(f"Reglamentos encontrados para {fecha_str}: {len(reglamentos)}")
            return reglamentos
            
        except Exception as e:
            logger.error(f"Error obteniendo reglamentos: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def _extraer_reglamentos_tabla(self, soup: BeautifulSoup, fecha: datetime) -> List[Dict]:
        """
        Extrae los reglamentos de la tabla HTML
        """
        reglamentos = []
        fecha_objetivo = fecha.strftime('%d/%m/%Y')
        
        # Buscar la tabla principal (debería ser la primera con muchas filas)
        tablas = soup.find_all('table')
        tabla_principal = None
        
        for tabla in tablas:
            filas = tabla.find_all('tr')
            if len(filas) > 100:  # La tabla principal tiene muchas filas
                tabla_principal = tabla
                break
        
        if not tabla_principal:
            logger.warning("No se encontró tabla principal de reglamentos")
            return []
        
        # Buscar filas de datos
        filas = tabla_principal.find_all('tr')
        logger.info(f"Procesando {len(filas)} filas de la tabla")
        
        for i, fila in enumerate(filas[1:], 1):  # Saltar header
            try:
                reglamento = self._extraer_info_reglamento(fila, fecha_objetivo)
                if reglamento:
                    reglamentos.append(reglamento)
                    logger.info(f"Reglamento encontrado: {reglamento.get('numero', 'N/A')}")
            except Exception as e:
                logger.debug(f"Error procesando fila {i}: {e}")
                continue
            
            # Limitar búsqueda a los primeros 200 para capturar más reglamentos
            if i > 200:
                break
        
        return reglamentos
    
    def _extraer_info_reglamento(self, fila, fecha_objetivo: str) -> Optional[Dict]:
        """
        Extrae información de un reglamento desde una fila de tabla
        Estructura esperada: [Expandir][Número][Año][Ministerio][Subsecretaría][Materia][Fecha][Estado][Descarga]
        """
        try:
            # Buscar celdas
            celdas = fila.find_all('td')
            if len(celdas) < 6:
                return None
            
            reglamento = {}
            
            # Número (celda 1)
            if len(celdas) > 1:
                numero_text = celdas[1].get_text(strip=True)
                reglamento['numero'] = numero_text
            
            # Año (celda 2)
            if len(celdas) > 2:
                ano_text = celdas[2].get_text(strip=True)
                reglamento['año'] = ano_text
            
            # Ministerio (celda 3)
            if len(celdas) > 3:
                ministerio_text = celdas[3].get_text(strip=True)
                reglamento['ministerio'] = ministerio_text
            
            # Subsecretaría (celda 4)
            if len(celdas) > 4:
                subsecretaria_text = celdas[4].get_text(strip=True)
                reglamento['subsecretaria'] = subsecretaria_text
            
            # Materia/Título (celda 5)
            if len(celdas) > 5:
                materia_text = celdas[5].get_text(strip=True)
                reglamento['materia'] = materia_text
                reglamento['titulo'] = materia_text
            
            # Fecha de ingreso (celda 6)
            fecha_text = ""
            if len(celdas) > 6:
                fecha_text = celdas[6].get_text(strip=True)
                reglamento['fecha_ingreso'] = fecha_text
            
            # Estado (celda 7 si existe)
            if len(celdas) > 7:
                estado_text = celdas[7].get_text(strip=True)
                reglamento['estado'] = estado_text
            
            # Solo incluir si es exactamente la fecha objetivo (día inmediatamente anterior)
            if fecha_text != fecha_objetivo:
                return None
            
            # Es exactamente la fecha que buscamos
            reglamento['es_objetivo'] = True
            
            # Buscar enlace de descarga en la última celda o en botones
            enlace_descarga = self._buscar_enlace_descarga(fila)
            if enlace_descarga:
                reglamento['url_descarga'] = enlace_descarga
            else:
                # URL por defecto a la página de reglamentos
                reglamento['url_descarga'] = self.reglamentos_url
            
            # Generar resumen
            reglamento['resumen'] = self._generar_resumen(reglamento)
            
            # Filtrar reglamentos mal parseados
            if not self._es_reglamento_valido(reglamento):
                return None
            
            return reglamento if reglamento.get('titulo') and reglamento.get('numero') else None
            
        except Exception as e:
            logger.debug(f"Error extrayendo reglamento: {e}")
            return None
    
    def _buscar_enlace_descarga(self, fila) -> Optional[str]:
        """
        Busca el enlace de descarga en la fila del reglamento
        """
        # Buscar enlaces PDF directos
        enlaces = fila.find_all('a', href=True)
        for enlace in enlaces:
            href = enlace.get('href', '')
            if '.pdf' in href.lower():
                if href.startswith('/'):
                    return self.base_url + href
                elif href.startswith('http'):
                    return href
        
        # Buscar texto "Descargar" o iconos de descarga
        elementos_descarga = fila.find_all(text=re.compile('Descargar|descargar'))
        for elem in elementos_descarga:
            parent = elem.parent if hasattr(elem, 'parent') else elem
            if parent and parent.name == 'a' and parent.get('href'):
                href = parent.get('href')
                if href.startswith('/'):
                    return self.base_url + href
                elif href.startswith('http'):
                    return href
        
        # Si no se encuentra enlace directo, retornar URL de la página de reglamentos
        return self.reglamentos_url
    
    def _es_fecha_reciente(self, fecha_text: str) -> bool:
        """
        Verifica si una fecha está dentro de los últimos días
        """
        try:
            # Intentar parsear diferentes formatos de fecha
            formatos = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
            fecha_obj = None
            
            for formato in formatos:
                try:
                    fecha_obj = datetime.strptime(fecha_text.strip(), formato)
                    break
                except:
                    continue
            
            if not fecha_obj:
                return False
            
            # Verificar si es de los últimos 3 días
            diferencia = datetime.now() - fecha_obj
            return diferencia.days <= 3
            
        except:
            return False
    
    def _es_fecha_reciente_flexible(self, fecha_text: str) -> bool:
        """
        Verifica si una fecha está dentro de los últimos días (más flexible)
        """
        if not fecha_text:
            return True  # Si no hay fecha, incluir por defecto para revisión manual
        
        try:
            # Limpiar texto de fecha
            fecha_limpia = fecha_text.strip()
            
            # Intentar parsear diferentes formatos
            formatos = [
                '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
                '%d.%m.%Y', '%d %m %Y', '%d/%m/%y'
            ]
            
            fecha_obj = None
            for formato in formatos:
                try:
                    fecha_obj = datetime.strptime(fecha_limpia, formato)
                    break
                except:
                    continue
            
            # Si no se pudo parsear, buscar año actual en el texto
            if not fecha_obj:
                año_actual = datetime.now().year
                if str(año_actual) in fecha_text or str(año_actual-1) in fecha_text:
                    return True  # Incluir si contiene año actual o anterior
                return False
            
            # Verificar si es de los últimos 30 días (más amplio para testing)
            diferencia = datetime.now() - fecha_obj
            return diferencia.days <= 30
            
        except:
            return True  # En caso de error, incluir para revisión manual
    
    def _generar_resumen(self, reglamento: Dict) -> str:
        """
        Genera un resumen del reglamento (solo la materia/título completo)
        """
        # Usar solo la materia/título sin cortar
        materia = reglamento.get('materia', '') or reglamento.get('titulo', '')
        if materia:
            # Asegurar que termine con punto
            materia = materia.strip()
            if not materia.endswith('.'):
                materia += '.'
            return materia
        return "Reglamento en tramitación."
    
    def _es_reglamento_valido(self, reglamento: Dict) -> bool:
        """
        Valida si un reglamento es válido y no está mal parseado
        """
        titulo = reglamento.get('titulo', '').lower()
        numero = reglamento.get('numero', '').lower()
        
        # Filtrar títulos que claramente no son reglamentos
        titulos_invalidos = ['descargar', 'ver', 'más', 'detalle', 'ampliar', 'expandir']
        if any(palabra in titulo for palabra in titulos_invalidos):
            return False
        
        # Filtrar números que son fechas o textos raros
        if numero and not any(char.isdigit() for char in numero):
            if 'n°' not in numero.lower() and not numero.isdigit():
                return False
        
        # Debe tener un título mínimamente descriptivo
        if len(titulo) < 10:
            return False
        
        return True

def test_scraper():
    """
    Función de prueba del scraper
    """
    print("\n🔍 PROBANDO SCRAPER DE REGLAMENTOS CONTRALORÍA")
    print("=" * 50)
    
    scraper = ScraperContraloriaReglamentos()
    
    # Probar con los últimos días para encontrar datos
    for dias_atras in range(1, 8):
        fecha_prueba = datetime.now() - timedelta(days=dias_atras)
        fecha_str = fecha_prueba.strftime('%d/%m/%Y')
        
        print(f"\n📅 Probando fecha: {fecha_str}")
        reglamentos = scraper.obtener_reglamentos_por_fecha(fecha_prueba)
        
        if reglamentos:
            print(f"✅ Encontrados {len(reglamentos)} reglamentos")
            
            for i, reg in enumerate(reglamentos[:2], 1):
                print(f"\n{i}. {reg.get('titulo', 'Sin título')}")
                print(f"   Número: {reg.get('numero', 'N/A')}")
                print(f"   Ministerio: {reg.get('ministerio', 'N/A')}")
                print(f"   Fecha: {reg.get('fecha_ingreso', 'N/A')}")
                print(f"   URL: {reg.get('url_descarga', 'N/A')}")
            
            break
        else:
            print(f"   No hay reglamentos para esta fecha")
    
    return reglamentos if 'reglamentos' in locals() else []

if __name__ == "__main__":
    test_scraper()