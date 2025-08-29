#!/usr/bin/env python3
"""
Scraper SEA FINAL - Usando Selenium con búsqueda específica
Solución definitiva que navega el sitio como un usuario real
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

logger = logging.getLogger(__name__)

class ScraperSEAFinal:
    def __init__(self):
        """Inicializa el scraper final con Selenium"""
        self.base_url = "https://seia.sea.gob.cl"
        # URL directa de búsqueda con proyectos recientes
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoAvanzada.php"
        # URL alternativa
        self.alt_url = f"{self.base_url}/busqueda/buscarProyecto.php"
        
    def _setup_driver(self):
        """Configura el driver de Chrome con opciones optimizadas"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Ocultar indicadores de automatización
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        return driver
    
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos recientes del SEIA navegando el sitio con Selenium
        """
        proyectos = []
        driver = None
        
        try:
            logger.info("🌊 Iniciando scraper SEA FINAL con Selenium...")
            driver = self._setup_driver()
            
            # Estrategia 1: Intentar búsqueda avanzada
            proyectos = self._buscar_con_formulario_avanzado(driver, dias_atras)
            
            # Estrategia 2: Si no funciona, probar búsqueda simple
            if not proyectos:
                logger.info("🔄 Intentando búsqueda alternativa...")
                proyectos = self._buscar_con_formulario_simple(driver, dias_atras)
            
            # Estrategia 3: Si aún no hay resultados, obtener de la página principal
            if not proyectos:
                logger.info("🔄 Obteniendo proyectos de la página principal...")
                proyectos = self._obtener_proyectos_recientes_home(driver)
            
            logger.info(f"✅ Total proyectos encontrados: {len(proyectos)}")
            
        except Exception as e:
            logger.error(f"❌ Error en scraper SEA Final: {str(e)}")
        finally:
            if driver:
                driver.quit()
        
        return proyectos[:50]  # Limitar a 50 proyectos
    
    def _buscar_con_formulario_avanzado(self, driver, dias_atras: int) -> List[Dict]:
        """Busca proyectos usando el formulario de búsqueda avanzada"""
        proyectos = []
        
        try:
            logger.info(f"📍 Navegando a búsqueda avanzada: {self.search_url}")
            driver.get(self.search_url)
            time.sleep(3)
            
            wait = WebDriverWait(driver, 10)
            
            # Configurar fechas
            fecha_hasta = datetime.now()
            fecha_desde = fecha_hasta - timedelta(days=dias_atras)
            
            # Buscar campos de fecha por diferentes métodos
            try:
                # Método 1: Por ID
                fecha_desde_input = driver.find_element(By.ID, "fecha_desde") or \
                                   driver.find_element(By.NAME, "fecha_desde") or \
                                   driver.find_element(By.XPATH, "//input[contains(@name, 'fecha') and contains(@name, 'desde')]")
                
                fecha_hasta_input = driver.find_element(By.ID, "fecha_hasta") or \
                                   driver.find_element(By.NAME, "fecha_hasta") or \
                                   driver.find_element(By.XPATH, "//input[contains(@name, 'fecha') and contains(@name, 'hasta')]")
                
                # Limpiar y llenar fechas
                fecha_desde_input.clear()
                fecha_desde_input.send_keys(fecha_desde.strftime("%d/%m/%Y"))
                
                fecha_hasta_input.clear()
                fecha_hasta_input.send_keys(fecha_hasta.strftime("%d/%m/%Y"))
                
                logger.info(f"📅 Buscando del {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}")
                
                # Buscar botón de búsqueda
                boton_buscar = driver.find_element(By.XPATH, "//input[@type='submit' and (@value='Buscar' or @value='BUSCAR')]") or \
                              driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar')]")
                
                boton_buscar.click()
                time.sleep(5)  # Esperar resultados
                
                # Extraer proyectos de los resultados
                proyectos = self._extraer_proyectos_de_pagina(driver)
                
            except Exception as e:
                logger.debug(f"No se pudo usar formulario avanzado: {e}")
                
        except Exception as e:
            logger.debug(f"Error en búsqueda avanzada: {e}")
        
        return proyectos
    
    def _buscar_con_formulario_simple(self, driver, dias_atras: int) -> List[Dict]:
        """Busca proyectos usando el formulario de búsqueda simple"""
        proyectos = []
        
        try:
            logger.info(f"📍 Navegando a búsqueda simple: {self.alt_url}")
            driver.get(self.alt_url)
            time.sleep(3)
            
            # Buscar cualquier tabla con proyectos
            proyectos = self._extraer_proyectos_de_pagina(driver)
            
        except Exception as e:
            logger.debug(f"Error en búsqueda simple: {e}")
        
        return proyectos
    
    def _obtener_proyectos_recientes_home(self, driver) -> List[Dict]:
        """Obtiene proyectos de la página principal"""
        proyectos = []
        
        try:
            logger.info(f"📍 Navegando a página principal: {self.base_url}")
            driver.get(self.base_url)
            time.sleep(3)
            
            # Buscar enlaces a proyectos recientes
            enlaces = driver.find_elements(By.XPATH, "//a[contains(@href, 'expediente') or contains(@href, 'proyecto')]")
            
            for enlace in enlaces[:20]:
                try:
                    texto = enlace.text.strip()
                    href = enlace.get_attribute('href')
                    
                    if texto and len(texto) > 10:
                        proyecto = {
                            'titulo': texto,
                            'url': href,
                            'fecha_presentacion': datetime.now().strftime('%d/%m/%Y')  # Fecha aproximada
                        }
                        
                        # Intentar extraer tipo del texto
                        if 'DIA' in texto:
                            proyecto['tipo'] = 'DIA'
                        elif 'EIA' in texto:
                            proyecto['tipo'] = 'EIA'
                        
                        proyectos.append(proyecto)
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error obteniendo proyectos de home: {e}")
        
        return proyectos
    
    def _extraer_proyectos_de_pagina(self, driver) -> List[Dict]:
        """Extrae proyectos de la página actual"""
        proyectos = []
        
        try:
            # Buscar todas las tablas
            tablas = driver.find_elements(By.TAG_NAME, "table")
            
            for tabla in tablas:
                try:
                    filas = tabla.find_elements(By.TAG_NAME, "tr")
                    
                    # Solo procesar tablas con contenido significativo
                    if len(filas) > 3:
                        logger.info(f"📊 Procesando tabla con {len(filas)} filas")
                        
                        # Detectar si es tabla de proyectos
                        header_text = filas[0].text.lower() if filas else ""
                        es_tabla_proyectos = any(palabra in header_text for palabra in ['proyecto', 'nombre', 'tipo', 'fecha'])
                        
                        for i, fila in enumerate(filas[1:], 1):
                            if i > 100:  # Limitar procesamiento
                                break
                            
                            proyecto = self._extraer_proyecto_de_fila_selenium(fila)
                            if proyecto:
                                proyectos.append(proyecto)
                                
                except Exception as e:
                    logger.debug(f"Error procesando tabla: {e}")
                    continue
            
            # Si no hay tablas, buscar en divs o listas
            if not proyectos:
                elementos = driver.find_elements(By.CLASS_NAME, "proyecto") + \
                           driver.find_elements(By.CLASS_NAME, "resultado") + \
                           driver.find_elements(By.XPATH, "//div[contains(@class, 'item')]")
                
                for elemento in elementos[:50]:
                    proyecto = self._extraer_proyecto_de_elemento_selenium(elemento)
                    if proyecto:
                        proyectos.append(proyecto)
            
        except Exception as e:
            logger.error(f"Error extrayendo proyectos: {e}")
        
        return proyectos
    
    def _extraer_proyecto_de_fila_selenium(self, fila) -> Optional[Dict]:
        """Extrae información de un proyecto desde una fila usando Selenium"""
        try:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            
            if len(celdas) < 2:
                return None
            
            proyecto = {}
            texto_completo = fila.text
            
            # Buscar información en cada celda
            for i, celda in enumerate(celdas):
                texto = celda.text.strip()
                
                # Primera celda con texto largo = título
                if i == 0 and len(texto) > 10:
                    proyecto['titulo'] = texto
                    # Buscar enlace
                    try:
                        enlace = celda.find_element(By.TAG_NAME, "a")
                        proyecto['url'] = enlace.get_attribute('href')
                        if not proyecto['titulo']:
                            proyecto['titulo'] = enlace.text.strip()
                    except:
                        pass
                
                # Detectar tipo
                if texto in ['DIA', 'EIA']:
                    proyecto['tipo'] = texto
                
                # Detectar fecha
                fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
                if fecha_match:
                    proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
                
                # Detectar región
                if 'Región' in texto or 'Metropolitana' in texto or 'Valparaíso' in texto:
                    proyecto['region'] = texto
                
                # Detectar estado
                if any(estado in texto for estado in ['En Calificación', 'En Admisión', 'Aprobado']):
                    proyecto['estado'] = texto
            
            # Validar proyecto
            if proyecto.get('titulo'):
                # Si no tiene fecha, buscar en texto completo
                if not proyecto.get('fecha_presentacion'):
                    fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto_completo)
                    if fecha_match:
                        proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
                
                return proyecto
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de fila: {e}")
            return None
    
    def _extraer_proyecto_de_elemento_selenium(self, elemento) -> Optional[Dict]:
        """Extrae información de un proyecto desde un elemento usando Selenium"""
        try:
            proyecto = {}
            texto = elemento.text.strip()
            
            # Buscar título
            try:
                titulo = elemento.find_element(By.TAG_NAME, "h3") or \
                        elemento.find_element(By.TAG_NAME, "a")
                proyecto['titulo'] = titulo.text.strip()
                
                if titulo.tag_name == 'a':
                    proyecto['url'] = titulo.get_attribute('href')
            except:
                if len(texto) > 20:
                    proyecto['titulo'] = texto.split('\n')[0]
            
            # Buscar fecha
            fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
            if fecha_match:
                proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
            
            # Detectar tipo
            if 'DIA' in texto:
                proyecto['tipo'] = 'DIA'
            elif 'EIA' in texto:
                proyecto['tipo'] = 'EIA'
            
            return proyecto if proyecto.get('titulo') else None
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de elemento: {e}")
            return None