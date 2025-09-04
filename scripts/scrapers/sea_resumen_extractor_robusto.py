#!/usr/bin/env python3
"""
Extractor robusto de resúmenes del SEA con Selenium
Implementa las mejores prácticas de hardening para producción
"""

import logging
import time
import re
import random
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, 
    StaleElementReferenceException,
    NoSuchElementException,
    WebDriverException
)
import os

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker para evitar martillar el SEA cuando está caído"""
    def __init__(self, failure_threshold=5, timeout_minutes=5):
        self.failure_threshold = failure_threshold
        self.timeout_minutes = timeout_minutes
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
    
    def call_succeeded(self):
        """Resetea el circuit breaker en caso de éxito"""
        self.failures = 0
        self.is_open = False
    
    def call_failed(self):
        """Registra una falla"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.is_open = True
            logger.error(f"🔴 Circuit breaker abierto después de {self.failures} fallas")
    
    def can_attempt(self) -> bool:
        """Verifica si podemos intentar una llamada"""
        if not self.is_open:
            return True
        
        # Verificar si ha pasado el tiempo de timeout
        if self.last_failure_time:
            elapsed = datetime.now() - self.last_failure_time
            if elapsed > timedelta(minutes=self.timeout_minutes):
                logger.info("🟡 Circuit breaker: intentando reconexión...")
                self.is_open = False
                self.failures = 0
                return True
        
        return False


class SEAResumenExtractorRobusto:
    """
    Extractor robusto con mejores prácticas de hardening
    """
    
    # Sinónimos de headers para búsqueda flexible
    HEADER_SYNONYMS = {
        'descripcion': ['descripción', 'descripcion', 'detalle del proyecto', 'objeto del proyecto', 
                        'resumen ejecutivo', 'antecedentes del proyecto', 'definición del proyecto'],
        'objetivo': ['objetivo', 'objetivos', 'finalidad', 'propósito'],
        'titular': ['titular', 'empresa', 'proponente', 'razón social', 'solicitante'],
        'ubicacion': ['ubicación', 'ubicacion', 'localización', 'localizacion', 'comuna', 'región', 'region'],
        'inversion': ['inversión', 'inversion', 'monto', 'capital', 'costo estimado']
    }
    
    # Timeouts por etapa
    TIMEOUTS = {
        'page_load': 30,
        'element_wait': 15,
        'frame_wait': 10,
        'max_per_project': 45  # Watchdog por proyecto
    }
    
    def __init__(self):
        self.driver = None
        self.base_url = "https://seia.sea.gob.cl"
        self.circuit_breaker = CircuitBreaker()
        self.retry_count = 3
        self.backoff_base = 1  # segundos
        
    def _setup_driver(self):
        """Configura el driver de Chrome con flags optimizados para Heroku"""
        if self.driver:
            return
            
        try:
            chrome_options = Options()
            
            # Flags recomendados para headless Chrome en Heroku
            chrome_options.add_argument("--headless=new")  # Versión nueva de headless
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")  # Crítico para Heroku
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Desactivar imágenes para acelerar carga
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Configuración para Heroku
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
                except Exception as e:
                    logger.error(f"No se pudo configurar Chrome en entorno local: {e}")
                    return None
            
            # Configurar timeouts
            self.driver.set_page_load_timeout(self.TIMEOUTS['page_load'])
            
        except Exception as e:
            logger.error(f"Error configurando Chrome: {e}")
            self.driver = None
    
    def _wait_for_element(self, by, value, timeout=None):
        """
        Espera inteligente por un elemento con reintentos ante StaleElement
        """
        timeout = timeout or self.TIMEOUTS['element_wait']
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                # Verificar que el elemento es estable
                time.sleep(0.5)
                _ = element.text  # Forzar acceso para verificar que no es stale
                return element
            except StaleElementReferenceException:
                if attempt < max_retries - 1:
                    logger.debug(f"Elemento stale, reintentando... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    raise
        return None
    
    def _find_by_header_synonyms(self, header_type: str) -> List:
        """
        Busca elementos usando sinónimos de headers
        """
        elements = []
        synonyms = self.HEADER_SYNONYMS.get(header_type, [])
        
        for synonym in synonyms:
            try:
                # Buscar con XPath normalizado
                xpath = f"//td[normalize-space(translate(., 'ÁÉÍÓÚÑ', 'AEIOUN'))='{synonym.upper()}']"
                found = self.driver.find_elements(By.XPATH, xpath)
                elements.extend(found)
                
                # También buscar con contains para ser más flexible
                xpath_contains = f"//td[contains(normalize-space(.), '{synonym}')]"
                found = self.driver.find_elements(By.XPATH, xpath_contains)
                elements.extend(found)
                
            except Exception as e:
                logger.debug(f"Error buscando sinónimo '{synonym}': {e}")
        
        return elements
    
    def _handle_frames(self):
        """
        Maneja frames de manera inteligente
        """
        try:
            frames = self.driver.find_elements(By.TAG_NAME, "frame") + \
                    self.driver.find_elements(By.TAG_NAME, "iframe")
            
            if not frames:
                return True  # No hay frames, estamos en el contexto principal
            
            for i, frame in enumerate(frames):
                try:
                    # Intentar cambiar al frame
                    self.driver.switch_to.frame(frame)
                    
                    # Verificar si estamos en el frame correcto buscando señales
                    signals = ["proyecto", "ficha", "descripción", "titular"]
                    page_text = self.driver.page_source.lower()
                    
                    if any(signal in page_text for signal in signals):
                        logger.debug(f"✅ Frame correcto encontrado (frame {i})")
                        return True
                    
                    # Si no es el frame correcto, volver al contexto principal
                    self.driver.switch_to.default_content()
                    
                except Exception as e:
                    logger.debug(f"Error procesando frame {i}: {e}")
                    self.driver.switch_to.default_content()
            
            # Si llegamos aquí, no encontramos el frame correcto
            logger.warning("No se encontró un frame con contenido del proyecto")
            return False
            
        except Exception as e:
            logger.error(f"Error manejando frames: {e}")
            return False
    
    def _extract_with_retry(self, id_expediente: str, attempt: int = 0) -> Dict[str, str]:
        """
        Extrae información con reintentos y backoff exponencial
        """
        if attempt >= self.retry_count:
            return {}
        
        try:
            # URL de la ficha
            url_ficha = f"{self.base_url}/expediente/ficha/fichaPrincipal.php?modo=ficha&id_expediente={id_expediente}"
            logger.info(f"🔄 Intento {attempt + 1}/{self.retry_count} - {url_ficha}")
            
            # Navegar a la página
            self.driver.get(url_ficha)
            
            # Manejar frames si existen
            self._handle_frames()
            
            # Esperar que carguen las tablas
            WebDriverWait(self.driver, self.TIMEOUTS['element_wait']).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Extraer información
            resultado = self._extract_from_tables()
            
            if resultado.get('resumen'):
                self.circuit_breaker.call_succeeded()
                return resultado
            else:
                raise ValueError("No se encontró resumen")
                
        except Exception as e:
            logger.warning(f"Intento {attempt + 1} falló: {e}")
            
            # Backoff exponencial con jitter
            wait_time = self.backoff_base * (2 ** attempt) + random.uniform(0, 1)
            logger.debug(f"Esperando {wait_time:.1f}s antes de reintentar...")
            time.sleep(wait_time)
            
            # Reintentar
            return self._extract_with_retry(id_expediente, attempt + 1)
    
    def _extract_from_tables(self) -> Dict[str, str]:
        """
        Extrae información de las tablas con búsqueda flexible
        """
        resultado = {
            'resumen': '',
            'objetivo': '',
            'titular': '',
            'ubicacion': '',
            'inversion': ''
        }
        
        try:
            # Buscar todas las tablas
            tablas = self.driver.find_elements(By.TAG_NAME, "table")
            
            for tabla in tablas:
                try:
                    filas = tabla.find_elements(By.TAG_NAME, "tr")
                    
                    for fila in filas:
                        celdas = fila.find_elements(By.TAG_NAME, "td")
                        if len(celdas) < 2:
                            celdas = fila.find_elements(By.TAG_NAME, "th") + celdas
                        
                        if len(celdas) >= 2:
                            header = self._normalize_text(celdas[0].text)
                            contenido = celdas[1].text.strip()
                            
                            # Buscar descripción con sinónimos
                            if not resultado['resumen'] and self._matches_header(header, 'descripcion'):
                                if contenido and len(contenido) > 100:
                                    resultado['resumen'] = self._clean_text(contenido)
                                    logger.info(f"✅ Resumen encontrado: {len(resultado['resumen'])} caracteres")
                            
                            # Buscar otros campos
                            elif not resultado['objetivo'] and self._matches_header(header, 'objetivo'):
                                if contenido:
                                    resultado['objetivo'] = self._clean_text(contenido)
                            
                            elif not resultado['titular'] and self._matches_header(header, 'titular'):
                                if contenido:
                                    resultado['titular'] = contenido
                            
                            elif not resultado['ubicacion'] and self._matches_header(header, 'ubicacion'):
                                if contenido:
                                    resultado['ubicacion'] = contenido
                            
                            elif not resultado['inversion'] and self._matches_header(header, 'inversion'):
                                if contenido:
                                    resultado['inversion'] = contenido
                                    
                except Exception as e:
                    logger.debug(f"Error procesando tabla: {e}")
                    continue
            
            # Si no encontramos resumen, buscar en otros elementos
            if not resultado['resumen']:
                resultado['resumen'] = self._extract_from_divs()
            
        except Exception as e:
            logger.error(f"Error extrayendo de tablas: {e}")
        
        return resultado
    
    def _extract_from_divs(self) -> str:
        """
        Busca resumen en divs y otros elementos como fallback
        """
        try:
            # XPaths flexibles para buscar contenido
            xpaths = [
                "//div[contains(@class, 'descripcion')]",
                "//div[contains(@class, 'resumen')]",
                "//div[contains(@class, 'detalle')]",
                "//div[contains(@class, 'contenido')]",
                "//p[string-length(.) > 300]",  # Párrafos largos
                "//*[contains(text(), 'El proyecto consiste')]",
                "//*[contains(text(), 'contempla')]"
            ]
            
            for xpath in xpaths:
                elementos = self.driver.find_elements(By.XPATH, xpath)
                for elemento in elementos:
                    texto = elemento.text.strip()
                    if self._is_valid_resumen(texto):
                        logger.info(f"✅ Resumen encontrado en elemento: {len(texto)} caracteres")
                        return self._clean_text(texto)
                        
        except Exception as e:
            logger.debug(f"Error buscando en divs: {e}")
        
        return ""
    
    def _matches_header(self, text: str, header_type: str) -> bool:
        """
        Verifica si un texto coincide con algún sinónimo del header
        """
        text_normalized = self._normalize_text(text)
        synonyms = self.HEADER_SYNONYMS.get(header_type, [])
        
        for synonym in synonyms:
            synonym_normalized = self._normalize_text(synonym)
            if synonym_normalized in text_normalized or text_normalized in synonym_normalized:
                return True
        
        return False
    
    def _normalize_text(self, text: str) -> str:
        """
        Normaliza texto para comparación
        """
        if not text:
            return ""
        
        # Remover acentos
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ñ': 'n', 'Ñ': 'N'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Convertir a minúsculas y remover espacios extra
        return ' '.join(text.lower().split())
    
    def _clean_text(self, text: str) -> str:
        """
        Limpia y normaliza el texto extraído
        """
        if not text:
            return ""
        
        # Remover caracteres no imprimibles
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
        
        # Colapsar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        # Remover espacios al inicio y final
        text = text.strip()
        
        # Si es muy largo, acortarlo inteligentemente
        if len(text) > 800:
            text = self._smart_truncate(text, 800)
        
        return text
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """
        Trunca texto de manera inteligente preservando información importante
        """
        if len(text) <= max_length:
            return text
        
        # Palabras clave prioritarias
        keywords = ['consiste', 'contempla', 'construcción', 'instalación', 
                   'operación', 'capacidad', 'MW', 'hectárea', 'producción']
        
        # Dividir en oraciones
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Priorizar oraciones con palabras clave
        prioritized = []
        normal = []
        
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in keywords):
                prioritized.append(sentence)
            else:
                normal.append(sentence)
        
        # Construir resultado
        result = []
        char_count = 0
        
        # Primero las priorizadas
        for sentence in prioritized:
            if char_count + len(sentence) < max_length - 3:
                result.append(sentence)
                char_count += len(sentence) + 1
        
        # Luego las normales si hay espacio
        for sentence in normal:
            if char_count + len(sentence) < max_length - 3:
                result.append(sentence)
                char_count += len(sentence) + 1
        
        final_text = ' '.join(result)
        if len(final_text) < len(text):
            final_text += '...'
        
        return final_text
    
    def _is_valid_resumen(self, text: str) -> bool:
        """
        Valida que un texto sea un resumen válido
        """
        if not text or len(text) < 200:
            return False
        
        # Debe contener palabras clave de proyecto
        keywords = ['proyecto', 'construcción', 'operación', 'instalación',
                   'contempla', 'consiste', 'desarrollar', 'implementar']
        
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
    
    def extraer_resumen_completo(self, id_expediente: str) -> Dict[str, str]:
        """
        Método principal para extraer resumen con todas las protecciones
        """
        # Verificar circuit breaker
        if not self.circuit_breaker.can_attempt():
            logger.warning("🔴 Circuit breaker abierto - usando fallback")
            return {}
        
        # Configurar driver si no existe
        self._setup_driver()
        
        if not self.driver:
            logger.error("No se pudo configurar el driver")
            return {}
        
        start_time = time.time()
        resultado = {}
        
        try:
            # Watchdog - tiempo máximo por proyecto
            resultado = self._extract_with_retry(id_expediente)
            
            elapsed = time.time() - start_time
            if elapsed > self.TIMEOUTS['max_per_project']:
                logger.warning(f"⏱️ Extracción tomó mucho tiempo: {elapsed:.1f}s")
            
        except TimeoutException:
            logger.error(f"⏰ Timeout extrayendo proyecto {id_expediente}")
            self.circuit_breaker.call_failed()
        except Exception as e:
            logger.error(f"❌ Error general extrayendo {id_expediente}: {e}")
            self.circuit_breaker.call_failed()
        
        return resultado
    
    def cerrar_driver(self):
        """Cierra el driver de Chrome de manera segura"""
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
            r'id=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.I)
            if match:
                return match.group(1)
        
        return None


# Instancia global con singleton para reutilizar driver
_instance = None

def get_extractor():
    """Obtiene la instancia singleton del extractor"""
    global _instance
    if _instance is None:
        _instance = SEAResumenExtractorRobusto()
    return _instance


if __name__ == "__main__":
    # Prueba
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*80)
    print("🛡️ PRUEBA DE EXTRACTOR ROBUSTO - PROYECTO MANQUEL SOLAR")
    print("="*80)
    
    extractor = get_extractor()
    
    try:
        id_proyecto = "2159854892"
        print(f"\nExtrayendo proyecto ID: {id_proyecto}")
        
        resultado = extractor.extraer_resumen_completo(id_proyecto)
        
        if resultado.get('resumen'):
            print("\n✅ RESUMEN EXTRAÍDO:")
            print("-"*60)
            print(resultado['resumen'][:600])
            print("-"*60)
        else:
            print("\n❌ No se pudo extraer (normal en local sin Selenium)")
            
    finally:
        extractor.cerrar_driver()