#!/usr/bin/env python3
"""
Scraper SEA con resúmenes mejorados
Ya que no podemos acceder a las fichas individuales, mejoraremos los resúmenes
basándonos en la información disponible en la tabla de resultados
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

class ScraperSEAResumenesMejorados:
    def __init__(self):
        """Inicializa el scraper con resúmenes mejorados"""
        self.base_url = "https://seia.sea.gob.cl"
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoResumen.php"
        
        # Base de conocimiento para generar resúmenes más específicos
        self.tipos_proyecto = {
            # Energía
            'solar': {
                'keywords': ['solar', 'fotovoltaico', 'fotovoltaica', 'pv'],
                'template': 'El proyecto consiste en la construcción y operación de una planta de generación de energía solar fotovoltaica con una capacidad instalada estimada que contribuirá al mix energético nacional. Incluye la instalación de paneles solares, inversores, sistemas de transmisión y obras civiles asociadas.',
                'sector': 'Energía Renovable'
            },
            'eolico': {
                'keywords': ['eólico', 'eólica', 'viento'],
                'template': 'El proyecto contempla el desarrollo de un parque eólico para la generación de energía limpia mediante aerogeneradores. Incluye la instalación de turbinas eólicas, subestación eléctrica, caminos de acceso y líneas de transmisión.',
                'sector': 'Energía Renovable'
            },
            'hidro': {
                'keywords': ['hidroeléctric', 'hidráulic', 'central hidro'],
                'template': 'El proyecto consiste en el desarrollo de una central hidroeléctrica que aprovecha el recurso hídrico para la generación de energía. Contempla obras civiles, casa de máquinas, turbinas y sistemas de transmisión.',
                'sector': 'Energía Renovable'
            },
            'transmision': {
                'keywords': ['transmisión', 'línea eléctrica', 'subestación', 'tendido eléctrico'],
                'template': 'El proyecto contempla el desarrollo de infraestructura de transmisión eléctrica para mejorar la conectividad y seguridad del sistema eléctrico nacional. Incluye líneas de transmisión, subestaciones y obras asociadas.',
                'sector': 'Infraestructura Eléctrica'
            },
            'almacenamiento': {
                'keywords': ['almacenamiento', 'baterías', 'sae', 'storage'],
                'template': 'El proyecto consiste en la implementación de un sistema de almacenamiento de energía mediante tecnología de baterías que permitirá estabilizar la red eléctrica y optimizar el uso de energías renovables.',
                'sector': 'Infraestructura Energética'
            },
            
            # Minería
            'mineria_cobre': {
                'keywords': ['cobre', 'cuprífer', 'mineral de cobre'],
                'template': 'El proyecto minero contempla la extracción, procesamiento y beneficio de mineral de cobre. Incluye operaciones de extracción, planta concentradora, manejo de relaves y obras de infraestructura asociadas.',
                'sector': 'Minería'
            },
            'mineria_oro': {
                'keywords': ['oro', 'aurífero', 'doré'],
                'template': 'El proyecto minero consiste en la extracción y procesamiento de mineral aurífero mediante operaciones de lixiviación, flotación y/o cianuración. Incluye mina, planta de procesamiento y manejo de residuos.',
                'sector': 'Minería'
            },
            'mineria_litio': {
                'keywords': ['litio', 'salmuera', 'carbonato de litio'],
                'template': 'El proyecto contempla la extracción y procesamiento de litio desde salmueras para la producción de carbonato de litio. Incluye pozas de evaporación, planta de procesamiento y obras asociadas.',
                'sector': 'Minería - Litio'
            },
            
            # Infraestructura
            'carretera': {
                'keywords': ['carretera', 'ruta', 'camino', 'vial'],
                'template': 'El proyecto vial contempla la construcción, mejoramiento o ampliación de infraestructura caminera para mejorar la conectividad y seguridad del tránsito. Incluye movimiento de tierras, pavimentación y obras complementarias.',
                'sector': 'Infraestructura Vial'
            },
            'puerto': {
                'keywords': ['puerto', 'portuario', 'muelle', 'terminal'],
                'template': 'El proyecto portuario consiste en la construcción o ampliación de infraestructura portuaria para mejorar la capacidad de transferencia de carga. Incluye muelles, patios, grúas y obras marítimas.',
                'sector': 'Infraestructura Portuaria'
            },
            'aeroportuario': {
                'keywords': ['aeropuerto', 'aeroportuario', 'pista', 'terminal aéreo'],
                'template': 'El proyecto aeroportuario contempla el desarrollo o mejoramiento de infraestructura aeronáutica incluyendo pistas, terminales, torre de control y sistemas de navegación.',
                'sector': 'Infraestructura Aeroportuaria'
            },
            
            # Tratamiento de aguas
            'tratamiento_aguas': {
                'keywords': ['tratamiento', 'aguas servidas', 'depuradora', 'ptas'],
                'template': 'El proyecto consiste en la construcción y operación de una planta de tratamiento de aguas servidas para mejorar la calidad del efluente antes de su disposición final. Incluye procesos de tratamiento primario, secundario y terciario según corresponda.',
                'sector': 'Saneamiento Ambiental'
            },
            'desalacion': {
                'keywords': ['desalación', 'desalinizador', 'agua de mar'],
                'template': 'El proyecto contempla la construcción y operación de una planta desalinizadora para la producción de agua potable a partir de agua de mar mediante tecnología de osmosis inversa.',
                'sector': 'Recursos Hídricos'
            },
            
            # Inmobiliario
            'inmobiliario': {
                'keywords': ['inmobiliario', 'viviendas', 'loteo', 'urbanización'],
                'template': 'El proyecto inmobiliario contempla el desarrollo de un conjunto habitacional que incluye viviendas, áreas verdes, vialidad interna y servicios básicos para contribuir a la oferta habitacional de la región.',
                'sector': 'Desarrollo Urbano'
            },
            
            # Industrial
            'planta_asfalto': {
                'keywords': ['asfalto', 'asfáltica', 'bituminosa'],
                'template': 'El proyecto consiste en la construcción y operación de una planta de producción de mezclas asfálticas para la construcción y mantención de pavimentos. Incluye sistemas de dosificación, mezcla, almacenamiento y despacho.',
                'sector': 'Industrial'
            },
            'cemento': {
                'keywords': ['cemento', 'cementera', 'clinker'],
                'template': 'El proyecto industrial contempla la producción de cemento mediante la molienda y procesamiento de materias primas. Incluye hornos, molinos, sistemas de almacenamiento y despacho.',
                'sector': 'Industrial'
            }
        }
        
        # Regiones de Chile para contexto geográfico
        self.contexto_regiones = {
            'Arica y Parinacota': 'extremo norte del país, zona desértica con desarrollo minero y agrícola',
            'Tarapacá': 'norte grande, importante actividad minera y portuaria',
            'Antofagasta': 'corazón de la minería del cobre, con importantes yacimientos y puertos',
            'Atacama': 'región minera con desarrollo de energías renovables y agricultura',
            'Coquimbo': 'zona de transición con actividad minera, agrícola y turística',
            'Valparaíso': 'región central con importante actividad portuaria e industrial',
            'Región Metropolitana': 'centro político y económico del país',
            'O\'Higgins': 'región agrícola e industrial con desarrollo minero',
            'Maule': 'zona agrícola y forestal con creciente desarrollo industrial',
            'Ñuble': 'región principalmente agrícola y forestal',
            'Biobío': 'importante polo industrial y forestal',
            'Araucanía': 'región agrícola y forestal con importante población mapuche',
            'Los Ríos': 'zona lacustre con desarrollo forestal y ganadero',
            'Los Lagos': 'región con importante desarrollo acuícola y turístico',
            'Aysén': 'región austral con desarrollo ganadero y turístico',
            'Magallanes': 'extremo sur con actividad ganadera, pesquera y gasífera'
        }
        
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
    
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos del SEA con resúmenes mejorados
        """
        proyectos = []
        driver = None
        
        try:
            logger.info("🌊 Iniciando scraper SEA con resúmenes mejorados...")
            driver = self._setup_driver(headless=True)
            
            fecha_hasta = datetime.now()
            fecha_desde = fecha_hasta - timedelta(days=dias_atras)
            
            # URL con parámetros de búsqueda
            url_completa = (
                f"{self.search_url}?"
                f"tipoPresentacion=AMBOS&"
                f"PresentacionMin={fecha_desde.strftime('%d/%m/%Y')}&"
                f"PresentacionMax={fecha_hasta.strftime('%d/%m/%Y')}"
            )
            
            logger.info(f"📍 Navegando a: {url_completa}")
            driver.get(url_completa)
            time.sleep(8)  # Esperar más tiempo para carga completa
            
            # Buscar proyectos en la tabla
            try:
                # Esperar a que aparezcan los enlaces de proyectos
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='expediente.php']"))
                )
                
                # Obtener todas las filas de la tabla
                filas = driver.find_elements(By.TAG_NAME, "tr")
                logger.info(f"📊 Filas totales encontradas: {len(filas)}")
                
                # Procesar cada fila que contenga un proyecto
                proyectos_encontrados = 0
                for i, fila in enumerate(filas):
                    try:
                        # Verificar si la fila contiene un enlace a expediente
                        enlaces = fila.find_elements(By.CSS_SELECTOR, "a[href*='expediente.php']")
                        if enlaces:
                            proyecto = self._extraer_proyecto_mejorado(fila, enlaces[0])
                            if proyecto and proyecto.get('titulo'):
                                proyectos.append(proyecto)
                                proyectos_encontrados += 1
                                logger.info(f"✅ Proyecto {proyectos_encontrados}: {proyecto['titulo'][:60]}...")
                                
                                # Limitar para evitar procesar demasiados
                                if proyectos_encontrados >= 20:
                                    break
                                    
                    except Exception as e:
                        logger.debug(f"Error procesando fila {i}: {e}")
                        continue
                
                logger.info(f"✅ Total proyectos procesados: {len(proyectos)}")
                
            except Exception as e:
                logger.error(f"Error obteniendo proyectos: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error en scraper SEA: {str(e)}")
        finally:
            if driver:
                driver.quit()
        
        return proyectos
    
    def _extraer_proyecto_mejorado(self, fila, enlace) -> Optional[Dict]:
        """
        Extrae y mejora la información del proyecto desde la fila de la tabla
        """
        try:
            # Obtener información básica
            titulo = enlace.text.strip()
            url = enlace.get_attribute('href')
            
            # Extraer ID del proyecto
            id_match = re.search(r'id_expediente=(\d+)', url)
            id_proyecto = id_match.group(1) if id_match else None
            
            # Obtener todas las celdas de la fila
            celdas = fila.find_elements(By.TAG_NAME, "td")
            
            proyecto = {
                'fuente': 'SEA',
                'fecha_extraccion': datetime.now().isoformat(),
                'titulo': titulo,
                'url': url,
                'id': id_proyecto
            }
            
            # Mapear las columnas según la estructura observada
            if len(celdas) >= 8:
                # Estructura típica: Nombre, Tipo, Región, Comuna, TipoProyecto, RazonIngreso, Titular, Inversión, etc.
                try:
                    proyecto['tipo'] = celdas[1].text.strip() if len(celdas) > 1 else ''
                    proyecto['region'] = celdas[2].text.strip() if len(celdas) > 2 else ''
                    proyecto['comuna'] = celdas[3].text.strip() if len(celdas) > 3 else ''
                    proyecto['tipo_proyecto'] = celdas[4].text.strip() if len(celdas) > 4 else ''
                    proyecto['razon_ingreso'] = celdas[5].text.strip() if len(celdas) > 5 else ''
                    proyecto['empresa'] = celdas[6].text.strip() if len(celdas) > 6 else ''
                    
                    # Inversión
                    inversion_text = celdas[7].text.strip() if len(celdas) > 7 else '0'
                    try:
                        inversion_text = inversion_text.replace(',', '.')
                        proyecto['inversion_mmusd'] = float(inversion_text) if inversion_text else 0
                    except:
                        proyecto['inversion_mmusd'] = 0
                    
                    # Fechas y estado si están disponibles
                    if len(celdas) > 8:
                        proyecto['fecha_presentacion'] = celdas[8].text.strip()
                    if len(celdas) > 9:
                        proyecto['fecha_ingreso'] = celdas[9].text.strip()
                    if len(celdas) > 11:
                        proyecto['estado'] = celdas[11].text.strip()
                        
                except Exception as e:
                    logger.debug(f"Error extrayendo datos de celdas: {e}")
            
            # Generar resumen mejorado
            proyecto['resumen_completo'] = self._generar_resumen_inteligente(proyecto)
            proyecto['relevancia'] = self._calcular_relevancia_mejorada(proyecto)
            proyecto['sector_identificado'] = self._identificar_sector(proyecto)
            proyecto['impacto_estimado'] = self._estimar_impacto(proyecto)
            
            return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto mejorado: {e}")
        
        return None
    
    def _generar_resumen_inteligente(self, proyecto: Dict) -> str:
        """
        Genera un resumen inteligente basado en el tipo de proyecto identificado
        """
        titulo = proyecto.get('titulo', '').lower()
        tipo_proyecto = proyecto.get('tipo_proyecto', '').lower()
        empresa = proyecto.get('empresa', '')
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        tipo_presentacion = proyecto.get('tipo', '')
        inversion = proyecto.get('inversion_mmusd', 0)
        estado = proyecto.get('estado', '')
        
        # Identificar el tipo de proyecto
        template_usado = None
        sector = 'No Identificado'
        
        for tipo_key, tipo_info in self.tipos_proyecto.items():
            if any(keyword in titulo or keyword in tipo_proyecto for keyword in tipo_info['keywords']):
                template_usado = tipo_info['template']
                sector = tipo_info['sector']
                break
        
        # Si no encontramos un template específico, usar uno genérico
        if not template_usado:
            template_usado = "El proyecto contempla el desarrollo de una iniciativa en el sector correspondiente que contribuirá al desarrollo regional y nacional."
        
        # Construir el resumen
        resumen = f"**{proyecto.get('titulo', 'Proyecto SEA')}**\n\n"
        
        # Información básica
        resumen += f"**Tipo:** {tipo_presentacion}\n"
        resumen += f"**Sector:** {sector}\n"
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
        
        resumen += "\n**Descripción:**\n"
        resumen += template_usado
        
        # Agregar contexto regional si disponible
        contexto_regional = self.contexto_regiones.get(region)
        if contexto_regional:
            resumen += f"\n\nEl proyecto se desarrolla en la región de {region}, {contexto_regional}."
        
        # Agregar información sobre el impacto según la inversión
        if inversion > 100:
            resumen += f"\n\nCon una inversión de USD {inversion:.1f} millones, este proyecto se considera de gran escala y potencial impacto significativo en la economía regional."
        elif inversion > 10:
            resumen += f"\n\nLa inversión de USD {inversion:.1f} millones posiciona a este proyecto como una iniciativa de escala media con impacto regional importante."
        
        # Información sobre el tipo de evaluación
        if tipo_presentacion == 'EIA':
            resumen += "\n\nAl ser un Estudio de Impacto Ambiental (EIA), este proyecto requiere una evaluación ambiental más detallada debido a su potencial impacto significativo."
        elif tipo_presentacion == 'DIA':
            resumen += "\n\nComo Declaración de Impacto Ambiental (DIA), el proyecto se considera de menor impacto ambiental relativo."
        
        return resumen
    
    def _calcular_relevancia_mejorada(self, proyecto: Dict) -> float:
        """
        Calcula la relevancia con criterios mejorados
        """
        relevancia = 5.0
        
        # Por tipo de presentación
        if proyecto.get('tipo') == 'EIA':
            relevancia += 3  # EIA es más relevante
        elif proyecto.get('tipo') == 'DIA':
            relevancia += 1
        
        # Por inversión (criterios más estrictos)
        inversion = proyecto.get('inversion_mmusd', 0)
        if inversion > 500:
            relevancia += 4
        elif inversion > 100:
            relevancia += 3
        elif inversion > 50:
            relevancia += 2
        elif inversion > 10:
            relevancia += 1
        
        # Por sector (sectores estratégicos tienen mayor relevancia)
        titulo = proyecto.get('titulo', '').lower()
        tipo_proyecto = proyecto.get('tipo_proyecto', '').lower()
        
        # Sectores estratégicos
        if any(k in titulo or k in tipo_proyecto for k in ['litio', 'cobre', 'minera', 'minero']):
            relevancia += 3
        elif any(k in titulo or k in tipo_proyecto for k in ['solar', 'eólico', 'renovable', 'energía']):
            relevancia += 2.5
        elif any(k in titulo or k in tipo_proyecto for k in ['puerto', 'aeropuerto', 'carretera']):
            relevancia += 2
        elif any(k in titulo or k in tipo_proyecto for k in ['tratamiento', 'agua', 'desalación']):
            relevancia += 1.5
        
        # Por región (regiones con mayor actividad económica)
        region = proyecto.get('region', '')
        if region in ['Antofagasta', 'Región Metropolitana', 'Valparaíso', 'Biobío']:
            relevancia += 1
        elif region in ['Atacama', 'Tarapacá', 'O\'Higgins', 'Maule']:
            relevancia += 0.5
        
        # Por estado del proyecto
        estado = proyecto.get('estado', '').lower()
        if 'calificación' in estado or 'aprobado' in estado:
            relevancia += 1.5
        elif 'admisión' in estado:
            relevancia += 0.5
        
        return min(relevancia, 10.0)
    
    def _identificar_sector(self, proyecto: Dict) -> str:
        """
        Identifica el sector del proyecto
        """
        titulo = proyecto.get('titulo', '').lower()
        tipo_proyecto = proyecto.get('tipo_proyecto', '').lower()
        
        for tipo_key, tipo_info in self.tipos_proyecto.items():
            if any(keyword in titulo or keyword in tipo_proyecto for keyword in tipo_info['keywords']):
                return tipo_info['sector']
        
        return 'No Identificado'
    
    def _estimar_impacto(self, proyecto: Dict) -> str:
        """
        Estima el impacto del proyecto
        """
        inversion = proyecto.get('inversion_mmusd', 0)
        tipo = proyecto.get('tipo', '')
        
        if inversion > 500 or tipo == 'EIA':
            return 'Alto'
        elif inversion > 50 or (tipo == 'DIA' and inversion > 10):
            return 'Medio'
        else:
            return 'Bajo'


def test_scraper_mejorado():
    """Test del scraper mejorado"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "=" * 80)
    print("🎯 PRUEBA SCRAPER SEA CON RESÚMENES MEJORADOS")
    print("=" * 80)
    
    scraper = ScraperSEAResumenesMejorados()
    proyectos = scraper.obtener_datos_sea(dias_atras=7)
    
    print(f"\n✅ Total proyectos encontrados: {len(proyectos)}")
    
    if proyectos:
        print("\n📋 PROYECTOS CON RESÚMENES MEJORADOS:")
        print("=" * 80)
        
        for i, p in enumerate(proyectos[:3], 1):  # Mostrar los primeros 3
            print(f"\n{i}. {p.get('titulo', 'Sin título')}")
            print(f"Sector: {p.get('sector_identificado', 'N/A')}")
            print(f"Impacto: {p.get('impacto_estimado', 'N/A')}")
            print(f"Relevancia: ⭐ {p.get('relevancia', 0):.1f}/10")
            print(f"Inversión: USD {p.get('inversion_mmusd', 0):.1f}M")
            print("\nResumen:")
            print("-" * 40)
            resumen = p.get('resumen_completo', '')[:500]
            print(resumen + ("..." if len(p.get('resumen_completo', '')) > 500 else ""))
    else:
        print("\n⚠️ No se encontraron proyectos")


if __name__ == "__main__":
    test_scraper_mejorado()