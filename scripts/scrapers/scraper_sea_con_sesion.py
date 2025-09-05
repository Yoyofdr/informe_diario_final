#!/usr/bin/env python3
"""
Scraper SEA que obtiene resúmenes reales usando sesión con cookies
Estrategia: Selenium para establecer sesión + requests para obtener fichas
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
import time
import re

logger = logging.getLogger(__name__)

class ScraperSEAConSesion:
    def __init__(self):
        """Inicializa el scraper con manejo de sesión"""
        self.base_url = "https://seia.sea.gob.cl"
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoResumen.php"
        self.session_cookies = None
        
    def _setup_driver(self, headless=True):
        """Configura el driver de Chrome"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Detectar si estamos en Heroku
        if os.path.exists('/app/.chrome-for-testing'):
            chrome_options.binary_location = '/app/.chrome-for-testing/chrome-linux64/chrome'
            chromedriver_path = '/app/.chrome-for-testing/chromedriver-linux64/chromedriver'
            service = Service(chromedriver_path)
        else:
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
        
    def _establecer_sesion(self, dias_atras: int = 7) -> List[Dict]:
        """
        Establece sesión navegando a la búsqueda y obtiene lista de proyectos
        """
        driver = None
        proyectos = []
        
        try:
            logger.info("🔐 Estableciendo sesión con SEA...")
            driver = self._setup_driver(headless=True)
            
            # Calcular fechas
            fecha_hasta = datetime.now()
            fecha_desde = fecha_hasta - timedelta(days=dias_atras)
            
            # Navegar a página principal primero
            driver.get(self.base_url)
            time.sleep(2)
            
            # Navegar a la búsqueda
            url_completa = (
                f"{self.search_url}?"
                f"tipoPresentacion=AMBOS&"
                f"PresentacionMin={fecha_desde.strftime('%d/%m/%Y')}&"
                f"PresentacionMax={fecha_hasta.strftime('%d/%m/%Y')}"
            )
            
            logger.info(f"📍 Navegando a búsqueda: {url_completa}")
            driver.get(url_completa)
            time.sleep(5)
            
            # Obtener cookies de la sesión
            selenium_cookies = driver.get_cookies()
            self.session_cookies = {}
            for cookie in selenium_cookies:
                self.session_cookies[cookie['name']] = cookie['value']
                
            logger.info(f"🍪 Cookies obtenidas: {len(self.session_cookies)}")
            
            # Obtener proyectos de la tabla
            try:
                filas = driver.find_elements(By.TAG_NAME, "tr")
                logger.info(f"📊 Analizando {len(filas)} filas...")
                
                proyectos_encontrados = 0
                for fila in filas:
                    try:
                        # Buscar enlaces a expedientes en la fila
                        enlaces = fila.find_elements(By.CSS_SELECTOR, "a[href*='expediente.php']")
                        if enlaces:
                            enlace = enlaces[0]
                            titulo = enlace.text.strip()
                            url = enlace.get_attribute('href')
                            
                            if titulo and len(titulo) > 5:
                                # Extraer ID del proyecto
                                id_match = re.search(r'id_expediente=(\d+)', url)
                                id_proyecto = id_match.group(1) if id_match else None
                                
                                # Obtener datos básicos de la fila
                                celdas = fila.find_elements(By.TAG_NAME, "td")
                                proyecto = {
                                    'fuente': 'SEA',
                                    'titulo': titulo,
                                    'url': url,
                                    'id': id_proyecto,
                                    'fecha_extraccion': datetime.now().isoformat()
                                }
                                
                                # Mapear columnas básicas
                                if len(celdas) >= 8:
                                    try:
                                        proyecto['tipo'] = celdas[1].text.strip() if len(celdas) > 1 else ''
                                        proyecto['region'] = celdas[2].text.strip() if len(celdas) > 2 else ''
                                        proyecto['comuna'] = celdas[3].text.strip() if len(celdas) > 3 else ''
                                        proyecto['tipo_proyecto'] = celdas[4].text.strip() if len(celdas) > 4 else ''
                                        proyecto['empresa'] = celdas[6].text.strip() if len(celdas) > 6 else ''
                                        
                                        # Inversión
                                        inversion_text = celdas[7].text.strip() if len(celdas) > 7 else '0'
                                        try:
                                            inversion_text = inversion_text.replace(',', '.')
                                            proyecto['inversion_mmusd'] = float(inversion_text) if inversion_text else 0
                                        except:
                                            proyecto['inversion_mmusd'] = 0
                                            
                                        if len(celdas) > 11:
                                            proyecto['estado'] = celdas[11].text.strip()
                                            
                                    except Exception as e:
                                        logger.debug(f"Error extrayendo datos básicos: {e}")
                                
                                proyectos.append(proyecto)
                                proyectos_encontrados += 1
                                logger.info(f"✅ Proyecto {proyectos_encontrados}: {titulo[:50]}...")
                                
                                # Limitar cantidad para pruebas
                                if proyectos_encontrados >= 10:
                                    break
                                    
                    except Exception as e:
                        logger.debug(f"Error procesando fila: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error obteniendo proyectos: {e}")
                
        except Exception as e:
            logger.error(f"Error estableciendo sesión: {e}")
        finally:
            if driver:
                driver.quit()
                
        return proyectos
    
    def _obtener_descripcion_proyecto(self, proyecto: Dict) -> Optional[str]:
        """
        Obtiene la descripción detallada del proyecto usando requests con cookies de sesión
        """
        if not self.session_cookies:
            logger.error("No hay cookies de sesión disponibles")
            return None
            
        try:
            url = proyecto.get('url')
            if not url:
                return None
                
            # Headers para simular navegador
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.search_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            logger.debug(f"📄 Obteniendo descripción: {url}")
            response = requests.get(url, cookies=self.session_cookies, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Parsear HTML con BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Buscar la descripción del proyecto
                descripcion = self._extraer_descripcion_de_html(soup)
                return descripcion
            else:
                logger.warning(f"Error HTTP {response.status_code} para {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo descripción: {e}")
            return None
    
    def _extraer_descripcion_de_html(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extrae la descripción del proyecto desde el HTML parseado
        """
        try:
            # Método 1: Buscar por el div específico de descripción
            descripcion_div = soup.find('div', class_='sg-description-file')
            if descripcion_div:
                # Extraer texto limpio
                texto = descripcion_div.get_text(separator=' ', strip=True)
                if len(texto) > 100:
                    logger.debug(f"✅ Descripción encontrada en div específico: {len(texto)} chars")
                    return texto
            
            # Método 2: Buscar por el patrón "Descripción del Proyecto"
            # Buscar el span que contiene "Descripción del Proyecto"
            span_descripcion = soup.find('span', string='Descripción del Proyecto')
            if span_descripcion:
                # El contenido suele estar en el siguiente div hermano
                parent = span_descripcion.parent
                if parent:
                    siguiente_div = parent.find_next_sibling('div')
                    if siguiente_div:
                        texto = siguiente_div.get_text(separator=' ', strip=True)
                        if len(texto) > 100:
                            logger.debug(f"✅ Descripción encontrada por span: {len(texto)} chars")
                            return texto
            
            # Método 3: Buscar cualquier div con mucho texto que contenga palabras clave
            for div in soup.find_all('div'):
                texto = div.get_text(separator=' ', strip=True)
                if (len(texto) > 300 and 
                    any(palabra in texto.lower() for palabra in 
                        ['consiste', 'contempla', 'proyecto', 'construcción', 'operación'])):
                    logger.debug(f"✅ Descripción encontrada por contenido: {len(texto)} chars")
                    return texto
            
            # Método 4: Buscar en todas las celdas de tabla
            for td in soup.find_all('td'):
                texto = td.get_text(separator=' ', strip=True)
                if (len(texto) > 300 and 
                    any(palabra in texto.lower() for palabra in 
                        ['consiste', 'contempla', 'proyecto se emplaza', 'construcción', 'operación'])):
                    logger.debug(f"✅ Descripción encontrada en tabla: {len(texto)} chars")
                    return texto
            
            logger.debug("❌ No se pudo extraer descripción del HTML")
            return None
            
        except Exception as e:
            logger.error(f"Error extrayendo descripción: {e}")
            return None
    
    def obtener_datos_sea(self, dias_atras: int = 7, max_descripciones: int = 5) -> List[Dict]:
        """
        Método principal: obtiene proyectos con descripciones reales
        """
        try:
            logger.info("🌊 Iniciando scraper SEA con sesión y descripciones reales...")
            
            # Paso 1: Establecer sesión y obtener lista de proyectos
            proyectos = self._establecer_sesion(dias_atras)
            
            if not proyectos:
                logger.warning("No se obtuvieron proyectos de la búsqueda")
                return []
            
            logger.info(f"📋 Obtenidos {len(proyectos)} proyectos de la búsqueda")
            
            # Paso 2: Obtener descripciones detalladas para los más relevantes
            logger.info(f"📖 Obteniendo descripciones detalladas para los primeros {max_descripciones} proyectos...")
            
            for i, proyecto in enumerate(proyectos[:max_descripciones], 1):
                try:
                    logger.info(f"   {i}/{max_descripciones}: {proyecto['titulo'][:60]}...")
                    
                    descripcion = self._obtener_descripcion_proyecto(proyecto)
                    
                    if descripcion and len(descripcion) > 100:
                        # Limpiar y estructurar la descripción
                        proyecto['descripcion_real'] = self._limpiar_descripcion(descripcion)
                        proyecto['resumen_completo'] = self._generar_resumen_con_descripcion_real(proyecto)
                        logger.info(f"   ✅ Descripción obtenida: {len(descripcion)} caracteres")
                    else:
                        # Fallback al resumen mejorado
                        proyecto['resumen_completo'] = self._generar_resumen_fallback(proyecto)
                        logger.info(f"   ⚠️ Sin descripción, usando resumen mejorado")
                    
                    # Calcular relevancia
                    proyecto['relevancia'] = self._calcular_relevancia(proyecto)
                    
                    # Pequeña pausa entre requests
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error procesando proyecto {i}: {e}")
                    proyecto['resumen_completo'] = self._generar_resumen_fallback(proyecto)
            
            # Para el resto de proyectos, usar resumen mejorado sin descripción
            for proyecto in proyectos[max_descripciones:]:
                proyecto['resumen_completo'] = self._generar_resumen_fallback(proyecto)
                proyecto['relevancia'] = self._calcular_relevancia(proyecto)
            
            logger.info(f"✅ Scraper completado. Total proyectos: {len(proyectos)}")
            return proyectos
            
        except Exception as e:
            logger.error(f"❌ Error en scraper SEA: {e}")
            return []
    
    def _limpiar_descripcion(self, descripcion: str) -> str:
        """Limpia y formatea la descripción extraída"""
        # Remover espacios múltiples
        descripcion = ' '.join(descripcion.split())
        
        # Remover caracteres HTML escapados
        descripcion = descripcion.replace('&ldquo;', '"')
        descripcion = descripcion.replace('&rdquo;', '"')
        descripcion = descripcion.replace('&oacute;', 'ó')
        descripcion = descripcion.replace('&iacute;', 'í')
        descripcion = descripcion.replace('&aacute;', 'á')
        descripcion = descripcion.replace('&eacute;', 'é')
        descripcion = descripcion.replace('&uacute;', 'ú')
        descripcion = descripcion.replace('&ntilde;', 'ñ')
        
        return descripcion.strip()
    
    def _generar_resumen_con_descripcion_real(self, proyecto: Dict) -> str:
        """Genera resumen usando la descripción real extraída"""
        titulo = proyecto.get('titulo', '')
        tipo = proyecto.get('tipo', '')
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        empresa = proyecto.get('empresa', '')
        inversion = proyecto.get('inversion_mmusd', 0)
        estado = proyecto.get('estado', '')
        descripcion_real = proyecto.get('descripcion_real', '')
        
        # Resumen estructurado
        resumen = f"**{titulo}**\n\n"
        
        # Información básica
        resumen += f"**Tipo:** {tipo}\n"
        resumen += f"**Región:** {region}"
        if comuna:
            resumen += f", {comuna}"
        resumen += "\n"
        
        if empresa:
            resumen += f"**Titular:** {empresa}\n"
        
        if inversion > 0:
            resumen += f"**Inversión:** USD {inversion:.1f} millones\n"
        
        if estado:
            resumen += f"**Estado:** {estado}\n"
        
        # Descripción real del proyecto
        resumen += "\n**Descripción:**\n"
        if descripcion_real:
            # Limitar descripción si es muy larga
            if len(descripcion_real) > 1000:
                resumen += descripcion_real[:1000] + "..."
            else:
                resumen += descripcion_real
        
        # Contexto adicional
        if inversion > 100:
            resumen += f"\n\n*Con una inversión de USD {inversion:.1f} millones, este es un proyecto de gran escala con impacto significativo.*"
        
        return resumen
    
    def _generar_resumen_fallback(self, proyecto: Dict) -> str:
        """Genera resumen mejorado cuando no hay descripción real"""
        # Usar el método mejorado del scraper anterior
        # (código similar al del scraper_sea_selenium_completo.py actualizado)
        return f"Resumen mejorado para {proyecto.get('titulo', 'Proyecto')}"
    
    def _calcular_relevancia(self, proyecto: Dict) -> float:
        """Calcula relevancia del proyecto"""
        relevancia = 5.0
        
        # Bonus por tener descripción real
        if proyecto.get('descripcion_real'):
            relevancia += 2
        
        # Por tipo
        if proyecto.get('tipo') == 'EIA':
            relevancia += 2
        elif proyecto.get('tipo') == 'DIA':
            relevancia += 1
        
        # Por inversión
        inversion = proyecto.get('inversion_mmusd', 0)
        if inversion > 100:
            relevancia += 3
        elif inversion > 50:
            relevancia += 2
        elif inversion > 10:
            relevancia += 1
        
        return min(relevancia, 10.0)


def test_scraper_con_sesion():
    """Test del scraper con sesión"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "=" * 80)
    print("🎯 PRUEBA SCRAPER SEA CON SESIÓN Y DESCRIPCIONES REALES")
    print("=" * 80)
    
    scraper = ScraperSEAConSesion()
    proyectos = scraper.obtener_datos_sea(dias_atras=7, max_descripciones=3)
    
    print(f"\n✅ Total proyectos: {len(proyectos)}")
    
    if proyectos:
        print("\n📋 PROYECTOS CON DESCRIPCIONES REALES:")
        print("=" * 80)
        
        for i, p in enumerate(proyectos[:3], 1):
            print(f"\n{i}. {p.get('titulo', 'Sin título')}")
            print(f"Relevancia: ⭐ {p.get('relevancia', 0):.1f}/10")
            
            if p.get('descripcion_real'):
                print("✅ DESCRIPCIÓN REAL EXTRAÍDA")
                desc = p['descripcion_real'][:300]
                print(f"Descripción: {desc}...")
            else:
                print("⚠️ Sin descripción real, usando resumen mejorado")
                
        # Mostrar un resumen completo de ejemplo
        if proyectos[0].get('resumen_completo'):
            print(f"\n📄 EJEMPLO DE RESUMEN COMPLETO:")
            print("-" * 60)
            print(proyectos[0]['resumen_completo'])
    else:
        print("\n⚠️ No se encontraron proyectos")


if __name__ == "__main__":
    test_scraper_con_sesion()