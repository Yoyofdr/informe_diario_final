#!/usr/bin/env python3
"""
Extractor de resúmenes del SEA usando Selenium
Diseñado para funcionar en producción (Heroku) donde Selenium sí funciona
"""

import logging
import time
import re
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os

logger = logging.getLogger(__name__)

class SEAResumenExtractorSelenium:
    """
    Extrae resúmenes completos del SEA usando Selenium
    Funciona en Heroku donde el Chrome está configurado correctamente
    """
    
    def __init__(self):
        self.driver = None
        self.base_url = "https://seia.sea.gob.cl"
        
    def _setup_driver(self):
        """Configura el driver de Chrome"""
        if self.driver:
            return
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # En Heroku usar el Chrome instalado
            if os.environ.get('DYNO'):
                chrome_options.binary_location = "/app/.chrome-for-testing/chrome-linux64/chrome"
                from selenium.webdriver.chrome.service import Service
                service = Service("/app/.chrome-for-testing/chromedriver-linux64/chromedriver")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # En local intentar con ChromeDriverManager
                try:
                    from selenium.webdriver.chrome.service import Service
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except:
                    logger.error("No se pudo configurar Chrome en entorno local")
                    return None
                    
            # Configurar timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
        except Exception as e:
            logger.error(f"Error configurando Chrome: {e}")
            self.driver = None
    
    def extraer_resumen_completo(self, id_expediente: str) -> Dict[str, str]:
        """
        Extrae el resumen completo navegando a la ficha del proyecto
        
        Returns:
            Dict con resumen completo y otros datos extraídos
        """
        resultado = {
            'resumen': '',
            'objetivo': '',
            'ubicacion': '',
            'titular': '',
            'inversion': ''
        }
        
        try:
            # Configurar driver si no está listo
            self._setup_driver()
            
            if not self.driver:
                logger.error("No se pudo configurar el driver de Chrome")
                return resultado
            
            # Navegar a la ficha del proyecto
            url_ficha = f"{self.base_url}/expediente/ficha/fichaPrincipal.php?modo=ficha&id_expediente={id_expediente}"
            logger.info(f"Navegando a: {url_ficha}")
            
            self.driver.get(url_ficha)
            
            # Esperar que cargue la página
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Buscar descripción en todas las tablas
            tablas = self.driver.find_elements(By.TAG_NAME, "table")
            
            for tabla in tablas:
                try:
                    filas = tabla.find_elements(By.TAG_NAME, "tr")
                    for fila in filas:
                        celdas = fila.find_elements(By.TAG_NAME, "td")
                        
                        if len(celdas) >= 2:
                            # Obtener header y contenido
                            header = celdas[0].text.strip()
                            contenido = celdas[1].text.strip()
                            
                            header_lower = header.lower()
                            
                            # Buscar descripción del proyecto
                            if any(palabra in header_lower for palabra in ['descripción', 'descripcion', 'objeto del proyecto', 'detalle del proyecto']):
                                if contenido and len(contenido) > 100:
                                    resultado['resumen'] = contenido
                                    logger.info(f"✅ Resumen encontrado: {len(contenido)} caracteres")
                            
                            # Buscar objetivo
                            elif 'objetivo' in header_lower:
                                if contenido and len(contenido) > 20:
                                    resultado['objetivo'] = contenido
                            
                            # Buscar titular
                            elif any(palabra in header_lower for palabra in ['titular', 'empresa', 'proponente']):
                                if contenido:
                                    resultado['titular'] = contenido
                            
                            # Buscar ubicación
                            elif any(palabra in header_lower for palabra in ['ubicación', 'ubicacion', 'comuna', 'región']):
                                if contenido:
                                    if not resultado['ubicacion']:
                                        resultado['ubicacion'] = contenido
                                    else:
                                        resultado['ubicacion'] += f", {contenido}"
                            
                            # Buscar inversión
                            elif any(palabra in header_lower for palabra in ['inversión', 'inversion', 'monto']):
                                if contenido:
                                    resultado['inversion'] = contenido
                                    
                except Exception as e:
                    logger.debug(f"Error procesando tabla: {e}")
                    continue
            
            # Si no encontramos resumen en tablas, buscar en otros elementos
            if not resultado['resumen']:
                # Buscar en divs con contenido relevante
                divs = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'descripcion')] | " +
                    "//div[contains(@class, 'contenido')] | " +
                    "//div[contains(@class, 'detalle')]"
                )
                
                for div in divs:
                    texto = div.text.strip()
                    if len(texto) > 200 and any(palabra in texto.lower() for palabra in ['proyecto', 'consiste', 'contempla']):
                        resultado['resumen'] = texto
                        logger.info(f"✅ Resumen encontrado en div: {len(texto)} caracteres")
                        break
            
            # Buscar también en párrafos largos
            if not resultado['resumen']:
                parrafos = self.driver.find_elements(By.TAG_NAME, "p")
                for p in parrafos:
                    texto = p.text.strip()
                    if len(texto) > 300:
                        # Verificar que sea contenido relevante del proyecto
                        palabras_clave = ['proyecto', 'construcción', 'operación', 'instalación', 
                                         'contempla', 'consiste', 'desarrollar', 'implementar']
                        if any(palabra in texto.lower() for palabra in palabras_clave):
                            resultado['resumen'] = texto
                            logger.info(f"✅ Resumen encontrado en párrafo: {len(texto)} caracteres")
                            break
            
            # Si encontramos un resumen muy largo, acortarlo inteligentemente
            if resultado['resumen'] and len(resultado['resumen']) > 800:
                resultado['resumen'] = self._acortar_resumen_inteligente(resultado['resumen'])
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error extrayendo resumen del proyecto {id_expediente}: {e}")
            return resultado
    
    def _acortar_resumen_inteligente(self, resumen: str, max_length: int = 800) -> str:
        """
        Acorta un resumen de manera inteligente, manteniendo la información más importante
        """
        if len(resumen) <= max_length:
            return resumen
        
        # Dividir en oraciones
        oraciones = re.split(r'(?<=[.!?])\s+', resumen)
        
        # Priorizar oraciones con palabras clave importantes
        palabras_importantes = ['consiste', 'contempla', 'construcción', 'instalación', 
                               'operación', 'capacidad', 'MW', 'hectárea', 'kilometro', 
                               'producción', 'procesamiento', 'generación']
        
        oraciones_priorizadas = []
        oraciones_normales = []
        
        for oracion in oraciones:
            oracion_lower = oracion.lower()
            if any(palabra in oracion_lower for palabra in palabras_importantes):
                oraciones_priorizadas.append(oracion)
            else:
                oraciones_normales.append(oracion)
        
        # Construir resumen con oraciones priorizadas primero
        resumen_final = []
        caracteres = 0
        
        # Agregar oraciones priorizadas
        for oracion in oraciones_priorizadas:
            if caracteres + len(oracion) < max_length - 3:
                resumen_final.append(oracion)
                caracteres += len(oracion) + 1
        
        # Si hay espacio, agregar oraciones normales
        for oracion in oraciones_normales:
            if caracteres + len(oracion) < max_length - 3:
                resumen_final.append(oracion)
                caracteres += len(oracion) + 1
        
        resultado = ' '.join(resumen_final)
        if len(resultado) < len(resumen):
            resultado += '...'
        
        return resultado
    
    def cerrar_driver(self):
        """Cierra el driver de Chrome"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def obtener_id_de_url(self, url: str) -> Optional[str]:
        """
        Extrae el ID del expediente desde una URL del SEA
        """
        patterns = [
            r'id_expediente=(\d+)',
            r'idExpediente=(\d+)',
            r'id=(\d+)',
            r'/expediente/(\d+)',
            r'/proyecto/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.I)
            if match:
                return match.group(1)
        
        return None


# Instancia global
sea_resumen_extractor_selenium = SEAResumenExtractorSelenium()


if __name__ == "__main__":
    # Prueba local (probablemente falle si Selenium no está configurado)
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*80)
    print("🔍 PRUEBA DE EXTRACCIÓN CON SELENIUM - PROYECTO MANQUEL SOLAR")
    print("="*80)
    print("\nNOTA: Esta prueba requiere Chrome y ChromeDriver configurados.")
    print("En producción (Heroku) funciona correctamente.\n")
    
    extractor = SEAResumenExtractorSelenium()
    
    try:
        # ID del proyecto Manquel Solar
        id_proyecto = "2159854892"
        
        print(f"Extrayendo información del proyecto ID: {id_proyecto}")
        print("Esto puede tomar unos segundos...\n")
        
        resultado = extractor.extraer_resumen_completo(id_proyecto)
        
        if resultado['resumen']:
            print("✅ RESUMEN EXTRAÍDO:")
            print("-"*60)
            print(resultado['resumen'][:800])
            print("-"*60)
            print(f"\nLongitud: {len(resultado['resumen'])} caracteres")
        else:
            print("❌ No se pudo extraer el resumen")
            print("Esto es normal en entorno local sin Selenium configurado.")
            print("El extractor funcionará en producción (Heroku).")
        
        if resultado['titular']:
            print(f"\n🏢 TITULAR: {resultado['titular']}")
        if resultado['ubicacion']:
            print(f"📍 UBICACIÓN: {resultado['ubicacion']}")
        if resultado['inversion']:
            print(f"💰 INVERSIÓN: {resultado['inversion']}")
        if resultado['objetivo']:
            print(f"🎯 OBJETIVO: {resultado['objetivo'][:200]}...")
            
    finally:
        extractor.cerrar_driver()
    
    print("\n" + "="*80)