#!/usr/bin/env python3
"""
Scraper SEA usando Playwright para obtener resúmenes ejecutivos reales
Navega a las fichas de proyecto y extrae la información completa
"""

from playwright.sync_api import sync_playwright, Page, Browser
from datetime import datetime, timedelta
import logging
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperSEAPlaywrightResumenes:
    def __init__(self):
        self.base_url = "https://seia.sea.gob.cl"
        self.ajax_endpoint = "/busqueda/buscarProyectoResumenAction.php"
        
        # Cache para resúmenes
        self.cache_dir = Path("cache_sea_playwright")
        self.cache_dir.mkdir(exist_ok=True)
        
        self.browser = None
        self.context = None
        self.page = None
        
    def iniciar_navegador(self):
        """Inicia Playwright con configuración optimizada"""
        if not self.browser:
            self.playwright = sync_playwright().start()
            
            # Configuración para evadir detección y mejorar rendimiento
            self.browser = self.playwright.chromium.launch(
                headless=True,  # Cambiar a False para debug
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Crear contexto con configuración realista
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='es-CL',
                timezone_id='America/Santiago'
            )
            
            # Agregar script para ocultar automatización
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.page = self.context.new_page()
            logger.info("✅ Navegador Playwright iniciado")
    
    def cerrar_navegador(self):
        """Cierra el navegador"""
        if self.browser:
            self.browser.close()
            self.playwright.stop()
            self.browser = None
            logger.info("🔚 Navegador cerrado")
    
    def obtener_lista_proyectos(self, dias_atras: int = 30) -> List[Dict]:
        """
        Obtiene la lista de proyectos usando el endpoint AJAX
        (más rápido que navegar por la interfaz)
        """
        import requests
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'{self.base_url}/busqueda/buscarProyectoResumen.php'
        })
        
        # Obtener cookies
        session.get(f"{self.base_url}/busqueda/buscarProyecto.php", timeout=30)
        
        # Preparar fechas
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=dias_atras)
        
        # Parámetros para el endpoint AJAX
        params = {
            'draw': '1',
            'start': '0',
            'length': '20',  # Limitar a 20 proyectos
            'fecha_desde': fecha_desde.strftime('%d/%m/%Y'),
            'fecha_hasta': fecha_hasta.strftime('%d/%m/%Y')
        }
        
        try:
            response = session.post(
                f"{self.base_url}{self.ajax_endpoint}",
                data=params,
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') and 'data' in data:
                    proyectos = []
                    for item in data['data']:
                        proyecto = {
                            'id_expediente': item.get('EXPEDIENTE_ID', ''),
                            'titulo': item.get('EXPEDIENTE_NOMBRE', ''),
                            'url_ficha': item.get('EXPEDIENTE_URL_FICHA', ''),
                            'tipo': item.get('WORKFLOW_DESCRIPCION', ''),
                            'region': item.get('REGION_NOMBRE', ''),
                            'comuna': item.get('COMUNA_NOMBRE', ''),
                            'titular': item.get('TITULAR', ''),
                            'inversion': item.get('INVERSION_MM_FORMAT', ''),
                            'fecha': item.get('FECHA_PRESENTACION_FORMAT', ''),
                            'estado': item.get('ESTADO_PROYECTO', ''),
                            'descripcion_tipologia': item.get('DESCRIPCION_TIPOLOGIA', '')
                        }
                        
                        # Asegurar URL completa
                        if proyecto['url_ficha'] and not proyecto['url_ficha'].startswith('http'):
                            proyecto['url_ficha'] = f"{self.base_url}{proyecto['url_ficha']}"
                        
                        proyectos.append(proyecto)
                    
                    logger.info(f"📊 {len(proyectos)} proyectos obtenidos del endpoint AJAX")
                    return proyectos
                    
        except Exception as e:
            logger.error(f"Error obteniendo lista de proyectos: {e}")
        
        return []
    
    def extraer_resumen_de_ficha(self, proyecto: Dict) -> Optional[str]:
        """
        Navega a la ficha del proyecto y extrae el resumen ejecutivo
        """
        id_expediente = proyecto.get('id_expediente')
        
        # Verificar cache
        cache_key = hashlib.md5(f"{id_expediente}".encode()).hexdigest()
        cache_file = self.cache_dir / f"resumen_{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('resumen'):
                        logger.info(f"📦 Resumen obtenido de cache para {proyecto['titulo'][:30]}...")
                        return data['resumen']
            except:
                pass
        
        if not self.page:
            self.iniciar_navegador()
        
        try:
            # Construir URL de la ficha
            url_ficha = f"{self.base_url}/expediente/expediente.php?id_expediente={id_expediente}"
            logger.info(f"🔍 Navegando a ficha de: {proyecto['titulo'][:50]}...")
            
            # Navegar a la ficha
            self.page.goto(url_ficha, wait_until='networkidle', timeout=30000)
            
            # Esperar un momento para que cargue
            self.page.wait_for_timeout(2000)
            
            # Verificar si hay frames
            frames = self.page.frames
            logger.info(f"   Frames encontrados: {len(frames)}")
            
            resumen = None
            
            # Buscar en el frame principal y en frames secundarios
            for frame in frames:
                try:
                    # Método 1: Buscar sección de descripción del proyecto
                    descripcion_elementos = frame.query_selector_all('text=/descripción del proyecto/i')
                    if descripcion_elementos:
                        for elem in descripcion_elementos:
                            # Buscar el contenedor padre y luego el texto siguiente
                            parent = elem.query_selector('xpath=..')
                            if parent:
                                texto = parent.inner_text()
                                if len(texto) > 100:  # Si tiene contenido significativo
                                    resumen = self._limpiar_resumen(texto)
                                    break
                    
                    # Método 2: Buscar en tablas
                    if not resumen:
                        tablas = frame.query_selector_all('table')
                        for tabla in tablas:
                            filas = tabla.query_selector_all('tr')
                            for fila in filas:
                                celdas = fila.query_selector_all('td, th')
                                if len(celdas) >= 2:
                                    etiqueta = celdas[0].inner_text().lower()
                                    if any(palabra in etiqueta for palabra in ['descripción', 'resumen', 'objetivo']):
                                        contenido = celdas[1].inner_text()
                                        if len(contenido) > 100:
                                            resumen = self._limpiar_resumen(contenido)
                                            break
                    
                    # Método 3: Buscar texto con patrones
                    if not resumen:
                        contenido_completo = frame.content()
                        
                        # Buscar patrones en el HTML
                        patrones = [
                            r'(?:El proyecto consiste en|Descripción del proyecto:?)\s*([^<]+(?:<[^>]+>[^<]+)*)',
                            r'<td[^>]*>([^<]*(?:consiste|comprende|contempla)[^<]+)</td>',
                            r'<p[^>]*>([^<]*(?:El proyecto|La iniciativa)[^<]+)</p>'
                        ]
                        
                        for patron in patrones:
                            matches = re.findall(patron, contenido_completo, re.IGNORECASE | re.DOTALL)
                            if matches:
                                # Limpiar HTML
                                texto = re.sub(r'<[^>]+>', ' ', matches[0])
                                texto = self._limpiar_resumen(texto)
                                if len(texto) > 100:
                                    resumen = texto
                                    break
                    
                    if resumen:
                        break
                        
                except Exception as e:
                    logger.debug(f"Error en frame: {e}")
            
            # Si encontramos resumen, guardarlo en cache
            if resumen:
                logger.info(f"✅ Resumen extraído ({len(resumen)} caracteres)")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'resumen': resumen,
                        'timestamp': datetime.now().isoformat()
                    }, f)
                return resumen
            else:
                logger.warning(f"⚠️ No se pudo extraer resumen de la ficha")
                
                # Guardar screenshot para debug
                self.page.screenshot(path=f"debug_ficha_{id_expediente}.png")
                
                # Generar resumen mejorado con la información disponible
                return self._generar_resumen_mejorado(proyecto)
                
        except Exception as e:
            logger.error(f"Error navegando a ficha: {e}")
            return self._generar_resumen_mejorado(proyecto)
    
    def _limpiar_resumen(self, texto: str) -> str:
        """Limpia y formatea el resumen extraído"""
        # Eliminar espacios múltiples y saltos de línea
        texto = ' '.join(texto.split())
        
        # Eliminar prefijos comunes
        prefijos = ['Descripción del proyecto:', 'Resumen:', 'Objetivo:']
        for prefijo in prefijos:
            if texto.startswith(prefijo):
                texto = texto[len(prefijo):].strip()
        
        # Limitar longitud
        if len(texto) > 500:
            # Intentar cortar en una oración completa
            punto = texto[:497].rfind('.')
            if punto > 300:
                texto = texto[:punto+1]
            else:
                texto = texto[:497] + "..."
        
        return texto
    
    def _generar_resumen_mejorado(self, proyecto: Dict) -> str:
        """Genera un resumen mejorado con la información disponible"""
        partes = []
        
        # Usar la descripción de tipología como base
        if proyecto.get('descripcion_tipologia'):
            partes.append(proyecto['descripcion_tipologia'])
        else:
            partes.append(f"{proyecto.get('tipo', 'Proyecto')} {proyecto.get('titulo', '')}")
        
        # Agregar información adicional
        if proyecto.get('titular'):
            partes.append(f"Titular: {proyecto['titular']}")
        
        ubicacion = []
        if proyecto.get('comuna'):
            ubicacion.append(proyecto['comuna'])
        if proyecto.get('region'):
            ubicacion.append(proyecto['region'])
        if ubicacion:
            partes.append(f"Ubicación: {', '.join(ubicacion)}")
        
        if proyecto.get('inversion'):
            partes.append(f"Inversión: USD {proyecto['inversion']}MM")
        
        if proyecto.get('estado'):
            partes.append(f"Estado: {proyecto['estado']}")
        
        resumen = ". ".join(partes)
        return resumen[:500] if len(resumen) > 500 else resumen
    
    def obtener_proyectos_con_resumenes(self, dias_atras: int = 30, max_proyectos: int = 10) -> List[Dict]:
        """
        Obtiene proyectos y extrae sus resúmenes ejecutivos
        """
        proyectos_con_resumenes = []
        
        try:
            # Obtener lista de proyectos
            proyectos = self.obtener_lista_proyectos(dias_atras)
            
            if not proyectos:
                logger.warning("No se encontraron proyectos")
                return []
            
            logger.info(f"📋 Procesando {min(len(proyectos), max_proyectos)} proyectos...")
            
            # Procesar cada proyecto
            for i, proyecto in enumerate(proyectos[:max_proyectos]):
                logger.info(f"\n[{i+1}/{min(len(proyectos), max_proyectos)}] Procesando: {proyecto['titulo'][:50]}...")
                
                # Extraer resumen de la ficha
                resumen = self.extraer_resumen_de_ficha(proyecto)
                
                if resumen:
                    proyecto['resumen'] = resumen
                else:
                    proyecto['resumen'] = self._generar_resumen_mejorado(proyecto)
                
                proyectos_con_resumenes.append(proyecto)
                
                # Pausa entre proyectos para no sobrecargar
                if i < max_proyectos - 1:
                    time.sleep(2)
            
            logger.info(f"\n✅ {len(proyectos_con_resumenes)} proyectos procesados con resúmenes")
            
        except Exception as e:
            logger.error(f"Error en obtener_proyectos_con_resumenes: {e}")
        finally:
            self.cerrar_navegador()
        
        return proyectos_con_resumenes

# Función de conveniencia
def obtener_proyectos_sea_playwright(dias_atras: int = 30, max_proyectos: int = 10) -> List[Dict]:
    """Obtiene proyectos del SEA con resúmenes usando Playwright"""
    scraper = ScraperSEAPlaywrightResumenes()
    return scraper.obtener_proyectos_con_resumenes(dias_atras, max_proyectos)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCRAPER SEA CON PLAYWRIGHT - EXTRACCIÓN DE RESÚMENES EJECUTIVOS")
    print("="*80)
    
    # Probar con pocos proyectos
    proyectos = obtener_proyectos_sea_playwright(dias_atras=30, max_proyectos=3)
    
    if proyectos:
        print(f"\n✅ Se procesaron {len(proyectos)} proyectos")
        
        for i, proyecto in enumerate(proyectos, 1):
            print(f"\n{'='*70}")
            print(f"PROYECTO {i}")
            print(f"{'='*70}")
            print(f"ID: {proyecto['id_expediente']}")
            print(f"Título: {proyecto['titulo']}")
            print(f"Tipo: {proyecto['tipo']}")
            print(f"Titular: {proyecto['titular']}")
            print(f"Región: {proyecto['region']}")
            print(f"Comuna: {proyecto['comuna']}")
            print(f"Inversión: USD {proyecto['inversion']}MM")
            print(f"Estado: {proyecto['estado']}")
            print(f"Fecha: {proyecto['fecha']}")
            
            print(f"\nRESUMEN ({len(proyecto.get('resumen', ''))} caracteres):")
            print("-"*70)
            import textwrap
            for linea in textwrap.wrap(proyecto.get('resumen', 'Sin resumen'), width=70):
                print(linea)
            print("-"*70)
    else:
        print("\n⚠️ No se encontraron proyectos")