#!/usr/bin/env python3
"""
Scraper SEA usando Selenium - Versión Completa
Navega a la tabla de proyectos y luego hace clic en cada proyecto para obtener detalles
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
        """Genera un resumen completo basado en los datos disponibles"""
        tipo = proyecto.get('tipo', 'Proyecto')
        empresa = proyecto.get('empresa', 'N/A')
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        tipo_proyecto = proyecto.get('tipo_proyecto', '')
        razon_ingreso = proyecto.get('razon_ingreso', '')
        estado = proyecto.get('estado', '')
        inversion = proyecto.get('inversion_mmusd', 0)
        
        resumen = f"Proyecto tipo {tipo}"
        
        if tipo_proyecto:
            resumen += f" ({tipo_proyecto})"
            
        if empresa and empresa != 'N/A':
            resumen += f" presentado por {empresa}"
        
        if region:
            resumen += f" en la {region}"
            if comuna:
                resumen += f", comuna de {comuna}"
        
        if razon_ingreso and 'tipología' not in razon_ingreso.lower():
            resumen += f". Razón de ingreso: {razon_ingreso}"
        
        if estado:
            resumen += f". Estado actual: {estado}"
        
        if inversion > 0:
            resumen += f". La inversión estimada es de USD {inversion:.1f} millones"
        
        # Agregar información específica según el tipo de proyecto
        titulo = proyecto.get('titulo', '').lower()
        if 'solar' in titulo or 'fotovolta' in titulo:
            resumen += ". El proyecto consiste en la construcción y operación de una planta de generación de energía solar fotovoltaica"
        elif 'tratamiento' in titulo and 'agua' in titulo:
            resumen += ". El proyecto consiste en la construcción y operación de una planta de tratamiento de aguas servidas"
        elif 'inmobiliario' in titulo:
            resumen += ". El proyecto consiste en el desarrollo de un proyecto inmobiliario"
        elif 'minera' in titulo or 'minero' in titulo:
            resumen += ". El proyecto está relacionado con actividades mineras"
        
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
        """Navega a la página del proyecto y obtiene el resumen detallado"""
        try:
            # Guardar la URL actual para volver
            url_actual = driver.current_url
            url_proyecto = proyecto.get('url')
            
            if not url_proyecto:
                return None
                
            logger.debug(f"📖 Navegando a: {url_proyecto}")
            driver.get(url_proyecto)
            time.sleep(3)  # Esperar que cargue la página
            
            # Extraer el resumen detallado del proyecto
            resumen_detallado = {}
            
            try:
                # Buscar el resumen en diferentes posibles ubicaciones
                # Opción 1: Buscar en tabla con label "Descripción"
                descripcion_elem = driver.find_elements(By.XPATH, 
                    "//td[contains(text(), 'Descripción')]/following-sibling::td | " +
                    "//th[contains(text(), 'Descripción')]/following-sibling::td | " + 
                    "//div[contains(@class, 'descripcion')] | " +
                    "//p[contains(@class, 'descripcion')]"
                )
                
                if descripcion_elem:
                    resumen_texto = descripcion_elem[0].text.strip()
                    if resumen_texto:
                        resumen_detallado['resumen_completo'] = resumen_texto
                        logger.debug(f"✅ Resumen encontrado: {len(resumen_texto)} caracteres")
                
                # Buscar objetivo del proyecto
                objetivo_elem = driver.find_elements(By.XPATH,
                    "//td[contains(text(), 'Objetivo')]/following-sibling::td | " +
                    "//th[contains(text(), 'Objetivo')]/following-sibling::td"
                )
                
                if objetivo_elem:
                    objetivo_texto = objetivo_elem[0].text.strip()
                    if objetivo_texto:
                        resumen_detallado['objetivo'] = objetivo_texto
                
                # Buscar ubicación detallada
                ubicacion_elem = driver.find_elements(By.XPATH,
                    "//td[contains(text(), 'Ubicación')]/following-sibling::td | " +
                    "//td[contains(text(), 'Localización')]/following-sibling::td"
                )
                
                if ubicacion_elem:
                    ubicacion_texto = ubicacion_elem[0].text.strip()
                    if ubicacion_texto:
                        resumen_detallado['ubicacion_detallada'] = ubicacion_texto
                
                # Si no encontramos un resumen específico, buscar en el contenido general
                if not resumen_detallado.get('resumen_completo'):
                    # Buscar específicamente en la sección de ficha del proyecto
                    ficha_proyecto = driver.find_elements(By.XPATH,
                        "//div[contains(@class, 'ficha')] | " +
                        "//div[contains(text(), 'Descripción del proyecto')] | " +
                        "//table[contains(@class, 'table')]"
                    )
                    
                    if ficha_proyecto:
                        # Buscar en todas las tablas de la página
                        tablas = driver.find_elements(By.TAG_NAME, "table")
                        for tabla in tablas:
                            # Buscar celdas que contengan "Descripción"
                            celdas = tabla.find_elements(By.TAG_NAME, "td")
                            for i, celda in enumerate(celdas):
                                if 'descripción' in celda.text.lower() and i < len(celdas) - 1:
                                    # La siguiente celda debería tener el contenido
                                    contenido = celdas[i + 1].text.strip()
                                    if contenido and len(contenido) > 50:
                                        resumen_detallado['resumen_completo'] = contenido
                                        break
                            if resumen_detallado.get('resumen_completo'):
                                break
                
                # Si aún no tenemos resumen, generar uno basado en los datos que tenemos
                if not resumen_detallado.get('resumen_completo'):
                    resumen_generado = self._generar_resumen(proyecto)
                    if proyecto.get('objetivo'):
                        resumen_generado += f". Objetivo: {proyecto['objetivo']}"
                    resumen_detallado['resumen_completo'] = resumen_generado
                    
            except Exception as e:
                logger.debug(f"Error extrayendo resumen: {e}")
            
            # Volver a la página de resultados
            driver.get(url_actual)
            time.sleep(2)
            
            return resumen_detallado if resumen_detallado else None
            
        except Exception as e:
            logger.debug(f"Error obteniendo resumen del proyecto: {e}")
            # Asegurarse de volver a la página principal
            try:
                driver.get(url_actual)
            except:
                pass
        
        return None
    
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