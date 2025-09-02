#!/usr/bin/env python3
"""
Scraper SEA usando Selenium para obtener proyectos recientes
Usa la página de búsqueda principal del SEIA
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

logger = logging.getLogger(__name__)

class ScraperSEASelenium:
    def __init__(self):
        """Inicializa el scraper con Selenium"""
        self.base_url = "https://seia.sea.gob.cl"
        self.search_url = f"{self.base_url}/busqueda/buscarProyecto.php"
        
    def _setup_driver(self):
        """Configura el driver de Chrome"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def obtener_resumen_proyecto(self, url_proyecto: str) -> str:
        """
        Obtiene el resumen ejecutivo de un proyecto desde su página de ficha
        """
        driver = None
        try:
            driver = self._setup_driver()
            driver.get(url_proyecto)
            time.sleep(2)
            
            # Buscar el resumen ejecutivo en varios posibles lugares
            resumen = ""
            
            # Buscar por texto "Resumen Ejecutivo" o similar
            elementos_resumen = driver.find_elements(By.XPATH, "//td[contains(text(), 'Resumen') or contains(text(), 'Descripción')]")
            
            for elemento in elementos_resumen:
                # Buscar el siguiente TD que contiene el texto del resumen
                try:
                    padre = elemento.find_element(By.XPATH, "..")
                    celdas = padre.find_elements(By.TAG_NAME, "td")
                    if len(celdas) > 1:
                        texto_resumen = celdas[-1].text.strip()
                        if texto_resumen and len(texto_resumen) > 50:
                            resumen = texto_resumen
                            break
                except:
                    pass
            
            # Si no encontramos resumen, buscar en divs con clase específica
            if not resumen:
                divs_contenido = driver.find_elements(By.CLASS_NAME, "contenido") + \
                                driver.find_elements(By.CLASS_NAME, "descripcion") + \
                                driver.find_elements(By.CLASS_NAME, "resumen")
                
                for div in divs_contenido:
                    texto = div.text.strip()
                    if texto and len(texto) > 100 and len(texto) < 5000:
                        resumen = texto
                        break
            
            # Buscar en tablas con información del proyecto
            if not resumen:
                tablas = driver.find_elements(By.TAG_NAME, "table")
                for tabla in tablas:
                    filas = tabla.find_elements(By.TAG_NAME, "tr")
                    for fila in filas:
                        celdas = fila.find_elements(By.TAG_NAME, "td")
                        if len(celdas) >= 2:
                            header = celdas[0].text.strip().lower()
                            if any(palabra in header for palabra in ['resumen', 'descripción', 'objeto', 'proyecto']):
                                contenido = celdas[1].text.strip()
                                if contenido and len(contenido) > 100:
                                    resumen = contenido
                                    break
                    if resumen:
                        break
            
            return resumen
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen del proyecto: {e}")
            return ""
        finally:
            if driver:
                driver.quit()
    
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos recientes del SEIA usando Selenium
        """
        proyectos = []
        driver = None
        
        try:
            logger.info("🌊 Iniciando scraper SEA con Selenium...")
            driver = self._setup_driver()
            
            # Acceder a la página de búsqueda
            logger.info(f"📍 Navegando a: {self.search_url}")
            driver.get(self.search_url)
            
            # Esperar que la página cargue
            wait = WebDriverWait(driver, 15)
            
            # Configurar fechas de búsqueda
            fecha_hasta = datetime.now()
            fecha_desde = fecha_hasta - timedelta(days=dias_atras)
            
            # Intentar llenar el formulario de búsqueda
            try:
                # Buscar campos de fecha
                fecha_desde_input = wait.until(
                    EC.presence_of_element_located((By.NAME, "fecha_desde"))
                )
                fecha_hasta_input = driver.find_element(By.NAME, "fecha_hasta")
                
                # Limpiar y llenar fechas
                fecha_desde_input.clear()
                fecha_desde_input.send_keys(fecha_desde.strftime("%d/%m/%Y"))
                
                fecha_hasta_input.clear()
                fecha_hasta_input.send_keys(fecha_hasta.strftime("%d/%m/%Y"))
                
                logger.info(f"📅 Buscando proyectos del {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}")
                
                # Hacer click en buscar
                boton_buscar = driver.find_element(By.XPATH, "//input[@value='Buscar' or @value='BUSCAR']")
                boton_buscar.click()
                
                # Esperar resultados
                time.sleep(3)
                
            except Exception as e:
                logger.warning(f"No se pudo usar el formulario: {e}")
                # Intentar obtener proyectos de la página principal
            
            # Buscar tabla de resultados
            tablas = driver.find_elements(By.TAG_NAME, "table")
            
            for tabla in tablas:
                try:
                    filas = tabla.find_elements(By.TAG_NAME, "tr")
                    
                    if len(filas) > 5:  # Tabla con contenido significativo
                        logger.info(f"📊 Procesando tabla con {len(filas)} filas")
                        
                        for i, fila in enumerate(filas[1:], 1):  # Saltar header
                            if i > 100:  # Limitar a 100 proyectos
                                break
                                
                            proyecto = self._extraer_proyecto_de_fila(fila)
                            if proyecto:
                                # Verificar fecha reciente
                                if self._es_proyecto_reciente(proyecto, dias_atras):
                                    # Intentar obtener resumen si tenemos URL
                                    if proyecto.get('url') and len(proyectos) < 10:  # Limitar para no demorar mucho
                                        resumen = self.obtener_resumen_proyecto(proyecto['url'])
                                        if resumen:
                                            proyecto['resumen'] = resumen[:1000]  # Limitar longitud
                                    
                                    proyectos.append(proyecto)
                                    logger.debug(f"✅ Proyecto encontrado: {proyecto.get('titulo', '')[:50]}...")
                                    
                except Exception as e:
                    logger.debug(f"Error procesando tabla: {e}")
                    continue
            
            # Si no encontramos proyectos, buscar en elementos específicos
            if not proyectos:
                logger.info("🔍 Buscando proyectos en elementos individuales...")
                
                # Buscar por clase o ID específicos
                elementos = driver.find_elements(By.CLASS_NAME, "proyecto") + \
                           driver.find_elements(By.CLASS_NAME, "resultado") + \
                           driver.find_elements(By.CLASS_NAME, "item")
                
                for elemento in elementos[:50]:
                    proyecto = self._extraer_proyecto_de_elemento(elemento)
                    if proyecto and self._es_proyecto_reciente(proyecto, dias_atras):
                        # Intentar obtener resumen si tenemos URL
                        if proyecto.get('url') and len(proyectos) < 10:
                            resumen = self.obtener_resumen_proyecto(proyecto['url'])
                            if resumen:
                                proyecto['resumen'] = resumen[:1000]
                        
                        proyectos.append(proyecto)
            
            logger.info(f"✅ Total proyectos encontrados: {len(proyectos)}")
            
        except Exception as e:
            logger.error(f"❌ Error en scraper SEA Selenium: {str(e)}")
        finally:
            if driver:
                driver.quit()
        
        return proyectos
    
    def _extraer_proyecto_de_fila(self, fila) -> Optional[Dict]:
        """Extrae información de proyecto desde una fila de tabla"""
        try:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            
            if len(celdas) < 3:
                return None
            
            proyecto = {}
            
            # Buscar información en las celdas
            for i, celda in enumerate(celdas):
                texto = celda.text.strip()
                
                # Detectar tipo de información
                if i == 0 and texto:  # Primera celda suele ser el nombre
                    proyecto['titulo'] = texto
                elif 'DIA' in texto or 'EIA' in texto:
                    proyecto['tipo'] = texto
                elif re.match(r'\d{2}/\d{2}/\d{4}', texto):
                    proyecto['fecha_presentacion'] = texto
                elif 'Región' in texto or any(r in texto for r in ['Metropolitana', 'Valparaíso', 'Biobío']):
                    proyecto['region'] = texto
                    
                # Buscar enlaces
                enlaces = celda.find_elements(By.TAG_NAME, "a")
                for enlace in enlaces:
                    href = enlace.get_attribute('href')
                    if href and 'expediente' in href.lower():
                        proyecto['url'] = href
                        if not proyecto.get('titulo'):
                            proyecto['titulo'] = enlace.text.strip()
            
            return proyecto if proyecto.get('titulo') else None
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de fila: {e}")
            return None
    
    def _extraer_proyecto_de_elemento(self, elemento) -> Optional[Dict]:
        """Extrae información de proyecto desde un elemento HTML"""
        try:
            proyecto = {}
            
            # Extraer texto completo
            texto = elemento.text.strip()
            
            # Buscar título en enlaces o headers
            titulo = elemento.find_elements(By.TAG_NAME, "h3") + \
                    elemento.find_elements(By.TAG_NAME, "h4") + \
                    elemento.find_elements(By.TAG_NAME, "a")
            
            if titulo:
                proyecto['titulo'] = titulo[0].text.strip()
            
            # Buscar fecha con regex
            fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
            if fecha_match:
                proyecto['fecha_presentacion'] = fecha_match.group(1)
            
            # Buscar tipo de proyecto
            if 'DIA' in texto:
                proyecto['tipo'] = 'DIA'
            elif 'EIA' in texto:
                proyecto['tipo'] = 'EIA'
            
            # Buscar región
            regiones = ['Metropolitana', 'Valparaíso', 'Biobío', 'Maule', 'Araucanía']
            for region in regiones:
                if region in texto:
                    proyecto['region'] = f'Región {region}'
                    break
            
            return proyecto if proyecto.get('titulo') else None
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de elemento: {e}")
            return None
    
    def _es_proyecto_reciente(self, proyecto: Dict, dias_atras: int) -> bool:
        """Verifica si un proyecto es reciente"""
        try:
            fecha_str = proyecto.get('fecha_presentacion', '')
            if not fecha_str:
                return False
            
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
            diferencia = datetime.now() - fecha
            
            return diferencia.days <= dias_atras
            
        except Exception:
            return False