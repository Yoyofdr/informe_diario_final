#!/usr/bin/env python3
"""
Extractor de resúmenes ejecutivos de proyectos SEA
Obtiene la descripción detallada de cada proyecto desde su ficha
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json

logger = logging.getLogger(__name__)

class SEAResumenExtractor:
    def __init__(self):
        self.base_url = "https://seia.sea.gob.cl"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8'
        })
    
    def extraer_resumen_proyecto(self, id_expediente: str) -> Dict[str, str]:
        """
        Extrae el resumen ejecutivo de un proyecto usando su ID
        """
        resultado = {
            'resumen': '',
            'inversion': '',
            'ubicacion': '',
            'titular': ''
        }
        
        try:
            # Intentar primero con requests directo
            resultado_requests = self._extraer_con_requests(id_expediente)
            if resultado_requests.get('resumen'):
                return resultado_requests
            
            # Si no funciona, intentar con Selenium
            logger.info(f"Intentando con Selenium para proyecto {id_expediente}")
            resultado_selenium = self._extraer_con_selenium(id_expediente)
            if resultado_selenium.get('resumen'):
                return resultado_selenium
                
        except Exception as e:
            logger.error(f"Error extrayendo resumen del proyecto {id_expediente}: {e}")
        
        return resultado
    
    def _extraer_con_requests(self, id_expediente: str) -> Dict[str, str]:
        """
        Intenta extraer información usando requests - Mejorado para mejor extracción
        """
        resultado = {
            'resumen': '',
            'inversion': '',
            'ubicacion': '',
            'titular': ''
        }
        
        # URLs a probar - incluir más endpoints
        urls = [
            f"{self.base_url}/expediente/expediente.php?id_expediente={id_expediente}",
            f"{self.base_url}/expediente/ficha/fichaPrincipal.php?modo=ficha&id_expediente={id_expediente}",
            f"{self.base_url}/expediente/expedientesEvaluacion.php?id_expediente={id_expediente}",
            f"{self.base_url}/documentos/documento.php?idDocumento={id_expediente}"  # Nueva URL
        ]
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=15, verify=False)  # Más tiempo y sin verificar SSL
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Eliminar scripts y estilos para obtener texto limpio
                for script in soup(['script', 'style']):
                    script.decompose()
                
                # Obtener texto completo
                texto = soup.get_text()
                lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
                
                # Buscar información en el texto - MEJORADO
                for i, linea in enumerate(lineas):
                    linea_lower = linea.lower()
                    
                    # Buscar descripción del proyecto con más variaciones
                    if any(desc in linea_lower for desc in ['descripción del proyecto', 'descripcion proyecto', 
                                                             'objetivo del proyecto', 'resumen ejecutivo',
                                                             'descripción general', 'el proyecto consiste']):
                        # Capturar las siguientes líneas hasta encontrar otra sección
                        descripcion_lineas = []
                        for j in range(i+1, min(i+30, len(lineas))):  # Más líneas
                            siguiente = lineas[j]
                            # Detener si encontramos otra sección
                            if any(seccion in siguiente.lower() for seccion in ['estado actual', 'titular', 'ubicación', 'menu', 'tabla']):
                                break
                            if len(siguiente.strip()) > 10:  # Solo líneas con contenido
                                descripcion_lineas.append(siguiente)
                        
                        if descripcion_lineas:
                            # Unir las líneas y tomar las oraciones importantes
                            texto_completo = ' '.join(descripcion_lineas)
                            # Limpiar espacios múltiples
                            texto_completo = ' '.join(texto_completo.split())
                            
                            # Si es muy largo, buscar las primeras 2-3 oraciones clave
                            if len(texto_completo) > 400:
                                oraciones = texto_completo.split('.')
                                resumen_corto = []
                                caracteres = 0
                                
                                for oracion in oraciones:
                                    oracion = oracion.strip()
                                    if oracion and caracteres + len(oracion) < 400:
                                        resumen_corto.append(oracion)
                                        caracteres += len(oracion)
                                        # Detenerse después de capturar la esencia
                                        if any(palabra in oracion.lower() for palabra in ['consiste', 'contempla', 'incluye', 'construcción', 'operación', 'extracción']):
                                            if caracteres > 150:  # Ya tenemos suficiente
                                                break
                                
                                if resumen_corto:
                                    resultado['resumen'] = '. '.join(resumen_corto) + '.'
                            else:
                                resultado['resumen'] = texto_completo
                    
                    # Buscar monto de inversión
                    elif 'monto de inversión' in linea_lower or 'inversión' in linea_lower:
                        # La siguiente línea suele tener el monto
                        if i+1 < len(lineas):
                            monto = lineas[i+1]
                            if any(moneda in monto for moneda in ['USD', 'US$', 'Dólares', 'Millones']):
                                resultado['inversion'] = monto
                    
                    # Buscar ubicación
                    elif 'comuna' in linea_lower or 'región' in linea_lower:
                        if not resultado['ubicacion'] and i+1 < len(lineas):
                            ubicacion = lineas[i] + ' ' + lineas[i+1] if i+1 < len(lineas) else lineas[i]
                            if any(lugar in ubicacion for lugar in ['Atacama', 'Copiapó', 'Antofagasta', 'Santiago', 'Valparaíso']):
                                resultado['ubicacion'] = ubicacion[:200]
                    
                    # Buscar titular
                    elif 'titular' in linea_lower or 'proponente' in linea_lower:
                        if i+1 < len(lineas):
                            posible_titular = lineas[i+1]
                            if len(posible_titular) > 5 and not any(skip in posible_titular.lower() for skip in ['menu', 'buscar', 'inicio']):
                                resultado['titular'] = posible_titular[:200]
                
                if resultado['resumen']:
                    logger.info(f"✅ Resumen encontrado con requests para {id_expediente}")
                    return resultado
                    
            except Exception as e:
                logger.debug(f"Error con URL {url}: {e}")
                continue
        
        return resultado
    
    def _extraer_con_selenium(self, id_expediente: str) -> Dict[str, str]:
        """
        Extrae información usando Selenium para páginas con JavaScript
        """
        resultado = {
            'resumen': '',
            'inversion': '',
            'ubicacion': '',
            'titular': ''
        }
        
        driver = None
        try:
            # Configurar Chrome
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # En Heroku usar el Chrome instalado
            import os
            if os.environ.get('DYNO'):
                chrome_options.binary_location = "/app/.chrome-for-testing/chrome-linux64/chrome"
                from selenium.webdriver.chrome.service import Service
                service = Service("/app/.chrome-for-testing/chromedriver-linux64/chromedriver")
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Navegar a la página
            url = f"{self.base_url}/expediente/ficha/fichaPrincipal.php?modo=ficha&id_expediente={id_expediente}"
            driver.get(url)
            
            # Esperar que cargue
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Buscar información en todas las tablas
            tablas = driver.find_elements(By.TAG_NAME, "table")
            
            for tabla in tablas:
                filas = tabla.find_elements(By.TAG_NAME, "tr")
                for fila in filas:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) >= 2:
                        header = celdas[0].text.strip().lower()
                        contenido = celdas[1].text.strip()
                        
                        # Mapear campos
                        if any(palabra in header for palabra in ['resumen', 'descripción', 'objeto']):
                            if len(contenido) > 100:
                                # Tomar solo las primeras oraciones relevantes
                                oraciones = contenido.split('.')
                                resumen = []
                                chars = 0
                                for oracion in oraciones[:3]:  # Máximo 3 oraciones
                                    if chars + len(oracion) < 400:
                                        resumen.append(oracion.strip())
                                        chars += len(oracion)
                                if resumen:
                                    resultado['resumen'] = '. '.join(resumen) + '.'
                                else:
                                    resultado['resumen'] = contenido[:400]
                        elif any(palabra in header for palabra in ['inversión', 'monto', 'usd', 'millones']):
                            resultado['inversion'] = contenido
                        elif any(palabra in header for palabra in ['ubicación', 'comuna', 'región']):
                            resultado['ubicacion'] = contenido
                        elif any(palabra in header for palabra in ['titular', 'proponente', 'empresa']):
                            resultado['titular'] = contenido
            
            # Si no encontramos resumen en tablas, buscar en divs
            if not resultado['resumen']:
                divs_contenido = driver.find_elements(By.CLASS_NAME, "contenido") + \
                                driver.find_elements(By.CLASS_NAME, "descripcion") + \
                                driver.find_elements(By.CLASS_NAME, "resumen")
                
                for div in divs_contenido:
                    texto = div.text.strip()
                    if texto and len(texto) > 200 and len(texto) < 5000:
                        resultado['resumen'] = texto[:2000]
                        break
            
            if resultado['resumen']:
                logger.info(f"✅ Resumen encontrado con Selenium para {id_expediente}")
            
        except Exception as e:
            logger.error(f"Error con Selenium: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return resultado
    
    def obtener_id_de_url(self, url: str) -> Optional[str]:
        """
        Extrae el ID del expediente desde una URL del SEA
        """
        # Buscar patrón id_expediente=XXXXX
        match = re.search(r'id_expediente=(\d+)', url)
        if match:
            return match.group(1)
        
        # Buscar otros patrones posibles
        match = re.search(r'/(\d{10,})', url)
        if match:
            return match.group(1)
        
        return None


# Instancia global
sea_resumen_extractor = SEAResumenExtractor()


if __name__ == "__main__":
    # Prueba con el proyecto Pimpollo
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*80)
    print("🔍 PRUEBA DE EXTRACCIÓN DE RESUMEN - PROYECTO PIMPOLLO")
    print("="*80)
    
    extractor = SEAResumenExtractor()
    
    # ID del proyecto Pimpollo
    id_pimpollo = "2166144419"
    
    print(f"\nExtrayendo información del proyecto ID: {id_pimpollo}")
    print("Esto puede tomar unos segundos...")
    resultado = extractor.extraer_resumen_proyecto(id_pimpollo)
    
    print("\n📊 RESULTADOS:")
    print("-"*40)
    
    if resultado['resumen']:
        print(f"✅ RESUMEN: {resultado['resumen'][:500]}...")
        print(f"   Longitud: {len(resultado['resumen'])} caracteres")
    else:
        print("❌ No se encontró resumen")
    
    if resultado['inversion']:
        print(f"💰 INVERSIÓN: {resultado['inversion']}")
    
    if resultado['ubicacion']:
        print(f"📍 UBICACIÓN: {resultado['ubicacion']}")
    
    if resultado['titular']:
        print(f"🏢 TITULAR: {resultado['titular']}")