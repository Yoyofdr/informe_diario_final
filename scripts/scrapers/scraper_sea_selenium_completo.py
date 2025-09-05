#!/usr/bin/env python3
"""
Scraper SEA usando Selenium - Versión Completa
Navega a la tabla de proyectos y luego hace clic en cada proyecto para obtener detalles
"""

import os
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

class ScraperSEASeleniumCompleto:
    def __init__(self):
        """Inicializa el scraper con Selenium"""
        self.base_url = "https://seia.sea.gob.cl"
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoResumen.php"
        
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
            # En Heroku, usar Chrome y ChromeDriver de Heroku
            chrome_options.binary_location = '/app/.chrome-for-testing/chrome-linux64/chrome'
            chromedriver_path = '/app/.chrome-for-testing/chromedriver-linux64/chromedriver'
            logger.info(f"🚀 Usando Chrome de Heroku: {chrome_options.binary_location}")
            logger.info(f"🚀 Usando ChromeDriver de Heroku: {chromedriver_path}")
            service = Service(chromedriver_path)
        else:
            # En local, usar webdriver-manager
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Ocultar indicadores de automatización
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos del SEA navegando la tabla y haciendo clic en cada proyecto
        """
        proyectos = []
        driver = None
        
        try:
            logger.info("🌊 Iniciando scraper SEA con Selenium (versión completa)...")
            driver = self._setup_driver(headless=True)
            
            fecha_hasta = datetime.now()
            fecha_desde = fecha_hasta - timedelta(days=dias_atras)
            
            # Construir URL con parámetros
            url_completa = (
                f"{self.search_url}?"
                f"tipoPresentacion=AMBOS&"
                f"PresentacionMin={fecha_desde.strftime('%d/%m/%Y')}&"
                f"PresentacionMax={fecha_hasta.strftime('%d/%m/%Y')}"
            )
            
            logger.info(f"📍 Navegando a: {url_completa}")
            driver.get(url_completa)
            
            # Esperar un poco más para que cargue JavaScript
            time.sleep(5)
            
            # Esperar a que aparezca la tabla
            wait = WebDriverWait(driver, 15)
            
            try:
                # Buscar la tabla de resultados
                tabla = wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                logger.info("✅ Tabla encontrada")
                
                # Obtener todas las filas de la tabla (excluyendo el header)
                filas = driver.find_elements(By.XPATH, "//table//tr[position()>1]")
                logger.info(f"📊 Filas encontradas: {len(filas)}")
                
                # Procesar cada fila
                for i, fila in enumerate(filas[:30], 1):  # Limitar a 30 proyectos
                    try:
                        proyecto = self._extraer_proyecto_de_fila(fila, driver)
                        if proyecto and proyecto.get('titulo'):
                            proyectos.append(proyecto)
                            logger.info(f"✅ Proyecto {i}: {proyecto.get('titulo', '')[:60]}")
                        else:
                            logger.debug(f"Fila {i} no contiene proyecto válido")
                                    
                    except Exception as e:
                        logger.debug(f"Error procesando fila {i}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"Error esperando tabla: {e}")
                
                # Plan B: Buscar elementos con clase específica
                logger.info("🔄 Intentando buscar proyectos por elementos div...")
                elementos = driver.find_elements(By.CLASS_NAME, "proyecto") + \
                           driver.find_elements(By.CLASS_NAME, "resultado")
                
                for elem in elementos[:20]:
                    proyecto = self._extraer_proyecto_de_elemento(elem)
                    if proyecto:
                        proyectos.append(proyecto)
            
            logger.info(f"✅ Total proyectos encontrados: {len(proyectos)}")
            
            # Obtener resúmenes detallados de los proyectos más relevantes
            if proyectos and len(proyectos) > 0:
                proyectos = self._obtener_resumenes_relevantes(proyectos, driver)
            
        except Exception as e:
            logger.error(f"❌ Error en scraper SEA Selenium: {str(e)}")
        finally:
            if driver:
                driver.quit()
        
        return proyectos
    
    def _obtener_resumenes_relevantes(self, proyectos: List[Dict], driver) -> List[Dict]:
        """Obtiene resúmenes detallados solo de los proyectos más relevantes"""
        logger.info("📄 Obteniendo resúmenes de proyectos relevantes...")
        
        # Ordenar por relevancia y tomar los más importantes
        proyectos_ordenados = sorted(proyectos, key=lambda x: x.get('relevancia', 0), reverse=True)
        
        # Obtener resúmenes de los top 5 o menos si hay menos proyectos
        max_resumenes = min(5, len(proyectos_ordenados))
        
        for i in range(max_resumenes):
            proyecto = proyectos_ordenados[i]
            try:
                logger.info(f"   Obteniendo resumen de: {proyecto.get('titulo', '')[:50]}...")
                resumen_detallado = self._obtener_resumen_proyecto(proyecto, driver)
                
                if resumen_detallado:
                    proyecto.update(resumen_detallado)
                    logger.info(f"   ✅ Resumen obtenido ({len(proyecto.get('resumen_completo', ''))} caracteres)")
                else:
                    # Si no se pudo obtener resumen detallado, generar uno básico
                    proyecto['resumen_completo'] = self._generar_resumen_completo(proyecto)
                    
            except Exception as e:
                logger.debug(f"Error obteniendo resumen: {e}")
                # Generar resumen básico si falla
                proyecto['resumen_completo'] = self._generar_resumen_completo(proyecto)
        
        # Para el resto de proyectos, generar resumen básico
        for i in range(max_resumenes, len(proyectos)):
            proyecto = proyectos[i]
            if not proyecto.get('resumen_completo'):
                proyecto['resumen_completo'] = self._generar_resumen_completo(proyecto)
        
        return proyectos
    
    def _generar_resumen_completo(self, proyecto: Dict) -> str:
        """Genera un resumen completo e inteligente basado en los datos disponibles"""
        titulo = proyecto.get('titulo', '').lower()
        tipo = proyecto.get('tipo', 'Proyecto')
        empresa = proyecto.get('empresa', 'N/A')
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        tipo_proyecto = proyecto.get('tipo_proyecto', '').lower()
        estado = proyecto.get('estado', '')
        inversion = proyecto.get('inversion_mmusd', 0)
        
        # Base de conocimiento para resúmenes específicos
        templates_especificos = {
            'solar': "El proyecto consiste en la construcción y operación de una planta de generación de energía solar fotovoltaica que contribuirá al mix energético renovable del país. Incluye la instalación de paneles solares, inversores, sistemas de transmisión y obras civiles asociadas.",
            'eolico': "El proyecto contempla el desarrollo de un parque eólico para la generación de energía limpia mediante aerogeneradores. Incluye la instalación de turbinas eólicas, subestación eléctrica, caminos de acceso y líneas de transmisión.",
            'almacenamiento': "El proyecto consiste en la implementación de un sistema de almacenamiento de energía mediante tecnología de baterías que permitirá estabilizar la red eléctrica y optimizar el uso de energías renovables.",
            'transmision': "El proyecto contempla el desarrollo de infraestructura de transmisión eléctrica para mejorar la conectividad y seguridad del sistema eléctrico nacional. Incluye líneas de transmisión, subestaciones y obras asociadas.",
            'mineria_cobre': "El proyecto minero contempla la extracción, procesamiento y beneficio de mineral de cobre. Incluye operaciones de extracción, planta concentradora, manejo de relaves y obras de infraestructura asociadas.",
            'mineria_oro': "El proyecto minero consiste en la extracción y procesamiento de mineral aurífero mediante operaciones de lixiviación, flotación y/o cianuración. Incluye mina, planta de procesamiento y manejo de residuos.",
            'mineria_litio': "El proyecto contempla la extracción y procesamiento de litio desde salmueras para la producción de carbonato de litio. Incluye pozas de evaporación, planta de procesamiento y obras asociadas.",
            'tratamiento_aguas': "El proyecto consiste en la construcción y operación de una planta de tratamiento de aguas servidas para mejorar la calidad del efluente antes de su disposición final. Incluye procesos de tratamiento primario, secundario y terciario según corresponda.",
            'desalacion': "El proyecto contempla la construcción y operación de una planta desalinizadora para la producción de agua potable a partir de agua de mar mediante tecnología de osmosis inversa.",
            'carretera': "El proyecto vial contempla la construcción, mejoramiento o ampliación de infraestructura caminera para mejorar la conectividad y seguridad del tránsito. Incluye movimiento de tierras, pavimentación y obras complementarias.",
            'puerto': "El proyecto portuario consiste en la construcción o ampliación de infraestructura portuaria para mejorar la capacidad de transferencia de carga. Incluye muelles, patios, grúas y obras marítimas.",
            'inmobiliario': "El proyecto inmobiliario contempla el desarrollo de un conjunto habitacional que incluye viviendas, áreas verdes, vialidad interna y servicios básicos para contribuir a la oferta habitacional de la región.",
            'planta_asfalto': "El proyecto consiste en la construcción y operación de una planta de producción de mezclas asfálticas para la construcción y mantención de pavimentos. Incluye sistemas de dosificación, mezcla, almacenamiento y despacho.",
            'cemento': "El proyecto industrial contempla la producción de cemento mediante la molienda y procesamiento de materias primas. Incluye hornos, molinos, sistemas de almacenamiento y despacho."
        }
        
        # Identificar el tipo de proyecto y obtener template específico
        descripcion_especifica = None
        sector_identificado = "No Identificado"
        
        # Energía
        if any(k in titulo or k in tipo_proyecto for k in ['solar', 'fotovoltaic', 'fotovoltaica', 'pv']):
            descripcion_especifica = templates_especificos['solar']
            sector_identificado = "Energía Renovable"
        elif any(k in titulo or k in tipo_proyecto for k in ['eólico', 'eólica', 'viento']):
            descripcion_especifica = templates_especificos['eolico']
            sector_identificado = "Energía Renovable"
        elif any(k in titulo or k in tipo_proyecto for k in ['almacenamiento', 'baterías', 'sae', 'storage']):
            descripcion_especifica = templates_especificos['almacenamiento']
            sector_identificado = "Infraestructura Energética"
        elif any(k in titulo or k in tipo_proyecto for k in ['transmisión', 'línea eléctrica', 'subestación']):
            descripcion_especifica = templates_especificos['transmision']
            sector_identificado = "Infraestructura Eléctrica"
        
        # Minería
        elif any(k in titulo or k in tipo_proyecto for k in ['cobre', 'cuprífer']):
            descripcion_especifica = templates_especificos['mineria_cobre']
            sector_identificado = "Minería"
        elif any(k in titulo or k in tipo_proyecto for k in ['oro', 'aurífero']):
            descripcion_especifica = templates_especificos['mineria_oro']
            sector_identificado = "Minería"
        elif any(k in titulo or k in tipo_proyecto for k in ['litio', 'salmuera']):
            descripcion_especifica = templates_especificos['mineria_litio']
            sector_identificado = "Minería - Litio"
        elif any(k in titulo or k in tipo_proyecto for k in ['minera', 'minero']):
            descripcion_especifica = templates_especificos['mineria_cobre']  # Default minero
            sector_identificado = "Minería"
        
        # Infraestructura
        elif any(k in titulo or k in tipo_proyecto for k in ['carretera', 'ruta', 'camino', 'vial']):
            descripcion_especifica = templates_especificos['carretera']
            sector_identificado = "Infraestructura Vial"
        elif any(k in titulo or k in tipo_proyecto for k in ['puerto', 'portuario', 'muelle']):
            descripcion_especifica = templates_especificos['puerto']
            sector_identificado = "Infraestructura Portuaria"
        
        # Tratamiento de aguas
        elif any(k in titulo or k in tipo_proyecto for k in ['tratamiento', 'aguas servidas', 'ptas']):
            descripcion_especifica = templates_especificos['tratamiento_aguas']
            sector_identificado = "Saneamiento Ambiental"
        elif any(k in titulo or k in tipo_proyecto for k in ['desalación', 'desalinizador']):
            descripcion_especifica = templates_especificos['desalacion']
            sector_identificado = "Recursos Hídricos"
        
        # Otros
        elif any(k in titulo or k in tipo_proyecto for k in ['inmobiliario', 'viviendas', 'loteo']):
            descripcion_especifica = templates_especificos['inmobiliario']
            sector_identificado = "Desarrollo Urbano"
        elif any(k in titulo or k in tipo_proyecto for k in ['asfalto', 'asfáltica']):
            descripcion_especifica = templates_especificos['planta_asfalto']
            sector_identificado = "Industrial"
        elif any(k in titulo or k in tipo_proyecto for k in ['cemento', 'cementera']):
            descripcion_especifica = templates_especificos['cemento']
            sector_identificado = "Industrial"
        
        # Construir resumen estructurado
        resumen = f"**{proyecto.get('titulo', 'Proyecto SEA')}**\n\n"
        
        # Información básica
        resumen += f"**Tipo:** {tipo}\n"
        resumen += f"**Sector:** {sector_identificado}\n"
        resumen += f"**Región:** {region}"
        if comuna:
            resumen += f", {comuna}"
        resumen += "\n"
        
        if empresa and empresa != 'N/A':
            resumen += f"**Titular:** {empresa}\n"
        
        if inversion > 0:
            resumen += f"**Inversión:** USD {inversion:.1f} millones\n"
        
        if estado:
            resumen += f"**Estado:** {estado}\n"
        
        # Descripción específica del proyecto
        resumen += "\n**Descripción:**\n"
        if descripcion_especifica:
            resumen += descripcion_especifica
        else:
            # Descripción genérica mejorada
            resumen += f"El proyecto contempla el desarrollo de una iniciativa en el sector {sector_identificado.lower()} que contribuirá al desarrollo regional y nacional."
        
        # Contexto adicional según inversión
        if inversion > 100:
            resumen += f"\n\nCon una inversión de USD {inversion:.1f} millones, este proyecto se considera de gran escala y potencial impacto significativo en la economía regional."
        elif inversion > 10:
            resumen += f"\n\nLa inversión de USD {inversion:.1f} millones posiciona a este proyecto como una iniciativa de escala media con impacto regional importante."
        
        # Información sobre el tipo de evaluación ambiental
        if tipo == 'EIA':
            resumen += "\n\nAl ser un Estudio de Impacto Ambiental (EIA), este proyecto requiere una evaluación ambiental más detallada debido a su potencial impacto significativo."
        elif tipo == 'DIA':
            resumen += "\n\nComo Declaración de Impacto Ambiental (DIA), el proyecto se considera de menor impacto ambiental relativo."
        
        return resumen
    
    def _extraer_proyecto_de_fila(self, fila, driver) -> Optional[Dict]:
        """Extrae información básica del proyecto desde una fila de la tabla"""
        try:
            # Obtener todas las celdas
            celdas = fila.find_elements(By.TAG_NAME, "td")
            
            if len(celdas) < 2:
                return None
            
            proyecto = {
                'fuente': 'SEA',
                'fecha_extraccion': datetime.now().isoformat()
            }
            
            # Mapeo típico de columnas basado en tu imagen:
            # 0: Nombre del Proyecto (con enlace)
            # 1: Tipo de Presentación (DIA/EIA)
            # 2: Región
            # 3: Comuna
            # 4: Tipo de Proyecto
            # 5: Razón de Ingreso
            # 6: Titular
            # 7: Inversión (MMUS$)
            # 8: Fecha Presentación
            # 9: Fecha de Ingreso
            # 10: Días Legales Transcurridos
            # 11: Estado del Proyecto
            
            # Columna 0: Nombre del proyecto con enlace
            if len(celdas) > 0:
                celda_nombre = celdas[0]
                enlace = celda_nombre.find_element(By.TAG_NAME, "a") if celda_nombre.find_elements(By.TAG_NAME, "a") else None
                
                if enlace:
                    proyecto['titulo'] = enlace.text.strip()
                    proyecto['url'] = enlace.get_attribute('href')
                    
                    # Extraer ID del href
                    id_match = re.search(r'id_expediente=(\d+)', proyecto['url'])
                    if id_match:
                        proyecto['id'] = id_match.group(1)
                else:
                    proyecto['titulo'] = celda_nombre.text.strip()
            
            # Columna 1: Tipo (DIA/EIA)
            if len(celdas) > 1:
                proyecto['tipo'] = celdas[1].text.strip()
            
            # Columna 2: Región
            if len(celdas) > 2:
                proyecto['region'] = celdas[2].text.strip()
            
            # Columna 3: Comuna
            if len(celdas) > 3:
                proyecto['comuna'] = celdas[3].text.strip()
            
            # Columna 4: Tipo de Proyecto
            if len(celdas) > 4:
                proyecto['tipo_proyecto'] = celdas[4].text.strip()
            
            # Columna 5: Razón de Ingreso
            if len(celdas) > 5:
                proyecto['razon_ingreso'] = celdas[5].text.strip()
            
            # Columna 6: Titular/Empresa
            if len(celdas) > 6:
                proyecto['empresa'] = celdas[6].text.strip()
            
            # Columna 7: Inversión
            if len(celdas) > 7:
                inversion_text = celdas[7].text.strip()
                # Convertir a número si es posible
                try:
                    # Remover comas y convertir
                    inversion_text = inversion_text.replace(',', '.')
                    proyecto['inversion_mmusd'] = float(inversion_text)
                except:
                    proyecto['inversion_mmusd'] = 0
            
            # Columna 8: Fecha Presentación
            if len(celdas) > 8:
                proyecto['fecha_presentacion'] = celdas[8].text.strip()
            
            # Columna 9: Fecha de Ingreso
            if len(celdas) > 9:
                proyecto['fecha_ingreso'] = celdas[9].text.strip()
            
            # Columna 10: Días Legales
            if len(celdas) > 10:
                dias_text = celdas[10].text.strip()
                try:
                    proyecto['dias_legales'] = int(dias_text)
                except:
                    proyecto['dias_legales'] = 0
            
            # Columna 11: Estado
            if len(celdas) > 11:
                proyecto['estado'] = celdas[11].text.strip()
            
            # Generar resumen
            if proyecto.get('titulo'):
                proyecto['resumen'] = self._generar_resumen(proyecto)
                proyecto['relevancia'] = self._calcular_relevancia(proyecto)
                return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de fila: {e}")
        
        return None
    
    def _obtener_resumen_proyecto(self, proyecto: Dict, driver) -> Optional[Dict]:
        """
        Obtiene resumen detallado del proyecto usando requests con cookies de Selenium
        NUEVO: Método híbrido que evita problemas de navegación con Selenium
        """
        try:
            url_proyecto = proyecto.get('url')
            if not url_proyecto:
                return None
            
            logger.debug(f"📖 Obteniendo resumen de: {url_proyecto}")
            
            # Método HÍBRIDO: usar requests con cookies de Selenium
            resumen_detallado = self._obtener_descripcion_con_requests(url_proyecto, driver)
            
            if resumen_detallado and resumen_detallado.get('resumen_completo'):
                logger.debug(f"✅ Descripción real obtenida: {len(resumen_detallado['resumen_completo'])} caracteres")
                return resumen_detallado
            else:
                # Fallback: generar resumen mejorado
                logger.debug("⚠️ Sin descripción real, usando resumen mejorado")
                return {'resumen_completo': self._generar_resumen_completo(proyecto)}
            
        except Exception as e:
            logger.debug(f"Error obteniendo resumen del proyecto: {e}")
            return {'resumen_completo': self._generar_resumen_completo(proyecto)}
    
    def _obtener_descripcion_con_requests(self, url_proyecto: str, driver) -> Optional[Dict]:
        """
        NUEVO: Obtiene descripción real usando requests con cookies de Selenium
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Obtener cookies de Selenium
            selenium_cookies = driver.get_cookies()
            cookies_dict = {}
            for cookie in selenium_cookies:
                cookies_dict[cookie['name']] = cookie['value']
            
            # Headers para simular navegador
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': driver.current_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Request con cookies de Selenium
            response = requests.get(url_proyecto, cookies=cookies_dict, headers=headers, timeout=20)
            
            if response.status_code == 200 and len(response.text) > 1000:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extraer descripción usando múltiples métodos
                descripcion = self._extraer_descripcion_de_soup(soup)
                
                if descripcion and len(descripcion) > 50:
                    return {
                        'resumen_completo': self._formatear_descripcion_real(descripcion),
                        'descripcion_real': descripcion,
                        'metodo_extraccion': 'requests_con_cookies'
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error en requests con cookies: {e}")
            return None
    
    def _extraer_descripcion_de_soup(self, soup) -> Optional[str]:
        """Extrae descripción del HTML parseado con BeautifulSoup"""
        
        # Método 1: Buscar div específico de descripción
        desc_div = soup.find('div', class_='sg-description-file')
        if desc_div:
            texto = desc_div.get_text(separator=' ', strip=True)
            if len(texto) > 50:
                return self._limpiar_texto_html(texto)
        
        # Método 2: Buscar por span "Descripción del Proyecto"  
        span_desc = soup.find('span', string='Descripción del Proyecto')
        if span_desc:
            parent = span_desc.parent
            if parent:
                siguiente = parent.find_next_sibling('div')
                if siguiente:
                    texto = siguiente.get_text(separator=' ', strip=True)
                    if len(texto) > 50:
                        return self._limpiar_texto_html(texto)
        
        # Método 3: Buscar divs con contenido relevante
        for div in soup.find_all('div'):
            texto = div.get_text(separator=' ', strip=True)
            if (len(texto) > 300 and 
                any(palabra in texto.lower() for palabra in 
                    ['consiste en', 'contempla', 'proyecto se emplaza', 'construcción', 'operación'])):
                return self._limpiar_texto_html(texto)
        
        # Método 4: Buscar en celdas de tabla
        for td in soup.find_all('td'):
            texto = td.get_text(separator=' ', strip=True)
            if (len(texto) > 300 and 
                any(palabra in texto.lower() for palabra in 
                    ['consiste en', 'contempla', 'se emplaza'])):
                return self._limpiar_texto_html(texto)
        
        return None
    
    def _limpiar_texto_html(self, texto: str) -> str:
        """Limpia texto extraído del HTML"""
        # Reemplazar entidades HTML
        replacements = {
            '&ldquo;': '"', '&rdquo;': '"', '&oacute;': 'ó', '&iacute;': 'í',
            '&aacute;': 'á', '&eacute;': 'é', '&uacute;': 'ú', '&ntilde;': 'ñ',
            '&Oacute;': 'Ó', '&Iacute;': 'Í', '&Aacute;': 'Á', '&Eacute;': 'É',
            '&Uacute;': 'Ú', '&Ntilde;': 'Ñ', '&nbsp;': ' '
        }
        
        for old, new in replacements.items():
            texto = texto.replace(old, new)
        
        # Limpiar espacios múltiples
        texto = ' '.join(texto.split())
        
        return texto.strip()
    
    def _formatear_descripcion_real(self, descripcion: str) -> str:
        """Formatea la descripción real para el resumen completo"""
        
        # Limpiar la descripción
        descripcion_limpia = self._limpiar_texto_html(descripcion)
        
        # Truncar si es muy larga
        if len(descripcion_limpia) > 1200:
            descripcion_limpia = descripcion_limpia[:1200] + "..."
        
        return descripcion_limpia
    
    def _extraer_proyecto_de_elemento(self, elemento) -> Optional[Dict]:
        """Extrae información de un proyecto desde un elemento div"""
        try:
            proyecto = {
                'fuente': 'SEA',
                'fecha_extraccion': datetime.now().isoformat()
            }
            
            # Buscar título
            titulo = elemento.find_element(By.TAG_NAME, "a") if elemento.find_elements(By.TAG_NAME, "a") else None
            if titulo:
                proyecto['titulo'] = titulo.text.strip()
                proyecto['url'] = titulo.get_attribute('href')
            else:
                proyecto['titulo'] = elemento.text.strip()[:100]
            
            # Buscar otros datos en el texto
            texto = elemento.text
            
            # Tipo
            if 'DIA' in texto:
                proyecto['tipo'] = 'DIA'
            elif 'EIA' in texto:
                proyecto['tipo'] = 'EIA'
            
            # Fecha
            fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
            if fecha_match:
                proyecto['fecha_presentacion'] = fecha_match.group(1)
            
            if proyecto.get('titulo') and len(proyecto['titulo']) > 5:
                proyecto['resumen'] = self._generar_resumen(proyecto)
                proyecto['relevancia'] = self._calcular_relevancia(proyecto)
                return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de elemento: {e}")
        
        return None
    
    def _generar_resumen(self, proyecto: Dict) -> str:
        """Genera un resumen del proyecto"""
        tipo = proyecto.get('tipo', 'Proyecto')
        empresa = proyecto.get('empresa', 'N/A')
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        estado = proyecto.get('estado', '')
        
        resumen = f"{tipo}"
        
        if empresa and empresa != 'N/A':
            resumen += f" presentado por {empresa}"
        
        if region:
            resumen += f" en {region}"
            if comuna:
                resumen += f", {comuna}"
        
        if estado:
            resumen += f". Estado: {estado}"
        
        inversion = proyecto.get('inversion_mmusd', 0)
        if inversion > 0:
            resumen += f". Inversión: USD {inversion:.1f}MM"
        
        return resumen
    
    def _calcular_relevancia(self, proyecto: Dict) -> float:
        """Calcula la relevancia del proyecto (0-10)"""
        relevancia = 5.0
        
        # Por tipo
        if proyecto.get('tipo') == 'EIA':
            relevancia += 2
        elif proyecto.get('tipo') == 'DIA':
            relevancia += 1
        
        # Por inversión
        inversion = proyecto.get('inversion_mmusd', 0)
        if inversion > 100:
            relevancia += 2
        elif inversion > 50:
            relevancia += 1.5
        elif inversion > 10:
            relevancia += 1
        
        # Por estado
        estado = proyecto.get('estado', '').lower()
        if 'calificación' in estado:
            relevancia += 1.5
        elif 'admisión' in estado:
            relevancia += 0.5
        
        # Por tipo de proyecto
        tipo_proyecto = proyecto.get('tipo_proyecto', '').lower()
        titulo = proyecto.get('titulo', '').lower()
        
        # Sectores prioritarios
        if any(s in titulo or s in tipo_proyecto for s in ['minera', 'minero', 'cobre', 'litio']):
            relevancia += 2
        elif any(s in titulo or s in tipo_proyecto for s in ['energía', 'solar', 'fotovoltaico', 'eólico']):
            relevancia += 1.5
        elif any(s in titulo or s in tipo_proyecto for s in ['inmobiliario', 'tratamiento', 'agua']):
            relevancia += 1
        
        return min(relevancia, 10)
    
    def verificar_proyectos_26_agosto(self, proyectos: List[Dict]):
        """Verifica si encontramos los proyectos específicos del 26/08"""
        proyectos_buscados = {
            "DIA Embalse Agromarchigue": False,
            "Parque Fotovoltaico Manquel Solar": False,
            "Planta de Tratamiento de Aguas Servidas El Cerrillo": False
        }
        
        logger.info("🔍 Verificando proyectos del 26-27/08/2025:")
        
        for p in proyectos:
            titulo = p.get('titulo', '').lower()
            
            # Verificar cada proyecto
            if 'agromarchigue' in titulo or 'embalse' in titulo:
                proyectos_buscados["DIA Embalse Agromarchigue"] = True
                logger.info(f"   ✅ DIA Embalse Agromarchigue - {p.get('fecha_presentacion', 'N/A')}")
            elif 'manquel' in titulo or ('parque' in titulo and 'solar' in titulo):
                proyectos_buscados["Parque Fotovoltaico Manquel Solar"] = True
                logger.info(f"   ✅ Parque Fotovoltaico Manquel Solar - {p.get('fecha_presentacion', 'N/A')}")
            elif 'cerrillo' in titulo or ('tratamiento' in titulo and 'agua' in titulo):
                proyectos_buscados["Planta de Tratamiento de Aguas Servidas El Cerrillo"] = True
                logger.info(f"   ✅ Planta de Tratamiento de Aguas - {p.get('fecha_presentacion', 'N/A')}")
        
        # Mostrar no encontrados
        for nombre, encontrado in proyectos_buscados.items():
            if not encontrado:
                logger.info(f"   ❌ {nombre} (NO ENCONTRADO)")
        
        return proyectos_buscados


def test_scraper():
    """Función de prueba del scraper"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "=" * 80)
    print("🎯 PRUEBA SCRAPER SEA CON SELENIUM COMPLETO")
    print("=" * 80)
    
    scraper = ScraperSEASeleniumCompleto()
    
    # Buscar proyectos de los últimos 3 días (para incluir el 26/08)
    proyectos = scraper.obtener_datos_sea(dias_atras=3)
    
    print(f"\n✅ Total proyectos encontrados: {len(proyectos)}")
    
    if proyectos:
        print("\n📋 PROYECTOS ENCONTRADOS:")
        print("-" * 80)
        
        for i, p in enumerate(proyectos[:10], 1):
            print(f"\n{i}. {p.get('titulo', 'Sin título')}")
            print(f"   Tipo: {p.get('tipo', 'N/A')}")
            print(f"   Empresa: {p.get('empresa', 'N/A')}")
            print(f"   Región: {p.get('region', 'N/A')}, {p.get('comuna', '')}")
            print(f"   Fecha presentación: {p.get('fecha_presentacion', 'N/A')}")
            print(f"   Estado: {p.get('estado', 'N/A')}")
            if p.get('inversion_mmusd', 0) > 0:
                print(f"   Inversión: USD {p['inversion_mmusd']:.2f}MM")
            print(f"   Relevancia: ⭐ {p.get('relevancia', 0):.1f}/10")
        
        # Verificar proyectos específicos
        print("\n" + "=" * 80)
        scraper.verificar_proyectos_26_agosto(proyectos)
    else:
        print("\n⚠️ No se encontraron proyectos")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_scraper()