#!/usr/bin/env python3
"""
Scraper integrado para datos ambientales del SEA
Usa scraper especializado para obtener proyectos del SEA
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Importar scrapers directamente sin fallbacks complejos
try:
    # Intentar importación relativa primero
    from .scraper_sea_selenium_completo import ScraperSEASeleniumCompleto
    logger.info("✅ Importado ScraperSEASeleniumCompleto (relativo)")
except ImportError:
    try:
        # Intentar importación absoluta
        from scripts.scrapers.scraper_sea_selenium_completo import ScraperSEASeleniumCompleto
        logger.info("✅ Importado ScraperSEASeleniumCompleto (absoluto)")
    except ImportError:
        try:
            # Intentar importación directa (cuando se ejecuta desde el mismo directorio)
            from scraper_sea_selenium_completo import ScraperSEASeleniumCompleto
            logger.info("✅ Importado ScraperSEASeleniumCompleto (directo)")
        except ImportError as e:
            logger.error(f"❌ Error importando ScraperSEASeleniumCompleto: {e}")
            ScraperSEASeleniumCompleto = None


# Importar telemetría
try:
    from telemetria_ambiental import TelemetriaScrapers
    telemetria = TelemetriaScrapers()
except ImportError:
    logger.warning("⚠️ Telemetría no disponible")
    telemetria = None

# Importar extractor robusto de resúmenes con Selenium (para producción)
sea_resumen_extractor_selenium = None
try:
    from .sea_resumen_extractor_robusto import get_extractor
    sea_resumen_extractor_selenium = get_extractor()
    logger.info("✅ Importado extractor ROBUSTO de resúmenes SEA con Selenium")
except ImportError:
    try:
        from scripts.scrapers.sea_resumen_extractor_robusto import get_extractor
        sea_resumen_extractor_selenium = get_extractor()
        logger.info("✅ Importado extractor ROBUSTO de resúmenes SEA (absoluto)")
    except ImportError:
        try:
            from sea_resumen_extractor_robusto import get_extractor
            sea_resumen_extractor_selenium = get_extractor()
            logger.info("✅ Importado extractor ROBUSTO de resúmenes SEA (directo)")
        except ImportError:
            # Fallback al extractor anterior
            try:
                from .sea_resumen_extractor_selenium import sea_resumen_extractor_selenium
                logger.info("✅ Importado extractor de resúmenes SEA con Selenium (versión anterior)")
            except ImportError:
                logger.warning("⚠️ Extractor con Selenium no disponible")
                sea_resumen_extractor_selenium = None

# Importar generador de resúmenes SEA (fallback sin conexión externa)
sea_resumen_generador = None
try:
    from .sea_resumen_generador import sea_resumen_generador
    logger.info("✅ Importado generador de resúmenes SEA (fallback)")
except ImportError:
    try:
        from scripts.scrapers.sea_resumen_generador import sea_resumen_generador
        logger.info("✅ Importado generador de resúmenes SEA (fallback - absoluto)")
    except ImportError:
        try:
            from sea_resumen_generador import sea_resumen_generador
            logger.info("✅ Importado generador de resúmenes SEA (fallback - directo)")
        except ImportError:
            logger.warning("⚠️ Generador de resúmenes SEA no disponible")
            sea_resumen_generador = None

class ScraperAmbiental:
    def __init__(self):
        """Inicializa el scraper ambiental integrado"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9'
        })
        
        # Inicializar scraper SEA
        if ScraperSEASeleniumCompleto:
            self.scraper_sea = ScraperSEASeleniumCompleto()
            logger.info("✅ Scraper SEA con Selenium inicializado")
        else:
            self.scraper_sea = None
            logger.error("❌ Scraper SEA no disponible")
    
    def obtener_datos_ambientales(self, dias_atras: int = 7) -> Dict:
        """
        Obtiene datos ambientales del SEA
        
        Args:
            dias_atras: Número de días hacia atrás para buscar
            
        Returns:
            Diccionario con proyectos SEA
        """
        logger.info(f"🔍 Obteniendo datos ambientales de los últimos {dias_atras} días...")
        
        inicio = time.time()
        errores_totales = []
        
        # Obtener proyectos SEA
        proyectos_sea = []
        if self.scraper_sea:
            try:
                logger.info("📋 Obteniendo proyectos SEA...")
                proyectos_sea = self._obtener_proyectos_sea(dias_atras)
                
                if telemetria:
                    telemetria.registrar_extraccion('SEA', {
                        'total_items': len(proyectos_sea),
                        'tiempo_ms': (time.time() - inicio) * 1000,
                        'exitoso': True
                    })
                    
                if proyectos_sea:
                    logger.info(f"✅ {len(proyectos_sea)} proyectos SEA encontrados")
                else:
                    logger.warning("⚠️ No se encontraron proyectos SEA")
                    errores_totales.append("SEA: No se encontraron proyectos")
                    
            except Exception as e:
                logger.error(f"❌ Error obteniendo datos SEA: {str(e)}")
                errores_totales.append(f"SEA: {str(e)}")
                
                if telemetria:
                    telemetria.registrar_extraccion('SEA', {
                        'total_items': 0,
                        'tiempo_ms': (time.time() - inicio) * 1000,
                        'exitoso': False,
                        'errores': [str(e)]
                    })
        else:
            logger.warning("⚠️ Scraper SEA no disponible")
            errores_totales.append("SEA: Scraper no disponible")
        
        
        tiempo_total = (time.time() - inicio) * 1000
        
        # Si hay errores, registrarlos
        if errores_totales:
            logger.error(f"❌ Errores registrados: {errores_totales}")
        
        datos = {
            'proyectos_sea': proyectos_sea,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'tiempo_total_ms': tiempo_total,
                'errores': errores_totales,
                'telemetria': {
                    'sea_items': len(proyectos_sea),
                    'total_items': len(proyectos_sea)
                }
            }
        }
        
        logger.info(f"✅ Datos ambientales obtenidos en {tiempo_total:.0f}ms - SEA: {len(proyectos_sea)}")
        
        return datos
    
    def _obtener_proyectos_sea(self, dias_atras: int) -> List[Dict]:
        """
        Obtiene proyectos del SEA usando el scraper con Selenium
        """
        try:
            logger.info(f"🔄 Obteniendo proyectos SEA de los últimos {dias_atras} días...")
            proyectos = self.scraper_sea.obtener_datos_sea(dias_atras=dias_atras)
            
            if proyectos:
                logger.info(f"✅ {len(proyectos)} proyectos SEA obtenidos")
                # Formatear para el informe
                proyectos_formateados = []
                for p in proyectos:
                    proyecto = {
                        'fuente': 'SEA',
                        'fecha_extraccion': datetime.now().isoformat(),
                        'titulo': p.get('titulo', ''),
                        'url': p.get('url', ''),
                        'id': p.get('id_expediente', ''),
                        'tipo': p.get('tipo', ''),
                        'region': p.get('region', ''),
                        'comuna': p.get('comuna', ''),
                        'tipo_proyecto': p.get('tipo_proyecto', ''),
                        'razon_ingreso': p.get('razon_ingreso', ''),
                        'empresa': p.get('empresa', p.get('titular', '')),
                        'inversion': p.get('inversion_mmusd', p.get('inversion', '')),
                        'fecha': p.get('fecha_presentacion', ''),
                        'resumen': p.get('resumen_completo', p.get('resumen', ''))
                    }
                    proyectos_formateados.append(proyecto)
                return proyectos_formateados
            else:
                logger.warning("⚠️ No se encontraron proyectos SEA")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error en _obtener_proyectos_sea: {str(e)}")
            raise
    
    
    def formatear_para_informe(self, datos_ambientales: Dict) -> Dict:
        """
        Formatea los datos ambientales para el informe HTML
        Solo usa datos REALES obtenidos del scraper SEA
        Incluye resúmenes ejecutivos de los proyectos
        """
        resultado = {
            'proyectos_sea': []
        }
        
        # Formatear proyectos SEA reales
        if datos_ambientales.get('proyectos_sea'):
            for proyecto in datos_ambientales['proyectos_sea']:
                # Solo incluir si tiene título (es un proyecto real)
                if proyecto.get('titulo'):
                    resumen_extraido = False
                    
                    # PRIMERO: Intentar extraer resumen real del SEA con Selenium (en producción)
                    if proyecto.get('url') and sea_resumen_extractor_selenium:
                        try:
                            id_expediente = sea_resumen_extractor_selenium.obtener_id_de_url(proyecto['url'])
                            if id_expediente:
                                logger.info(f"🔍 Intentando extraer resumen real del SEA para {proyecto['titulo'][:30]}...")
                                resultado_sea = sea_resumen_extractor_selenium.extraer_resumen_completo(id_expediente)
                                
                                if resultado_sea.get('resumen'):
                                    proyecto['resumen'] = resultado_sea['resumen']
                                    resumen_extraido = True
                                    logger.info(f"✅ Resumen real extraído del SEA ({len(proyecto['resumen'])} caracteres)")
                                    
                                    # Agregar otros datos si los encontramos
                                    if resultado_sea.get('titular') and not proyecto.get('empresa'):
                                        proyecto['empresa'] = resultado_sea['titular']
                                    if resultado_sea.get('ubicacion') and not proyecto.get('ubicacion'):
                                        proyecto['ubicacion'] = resultado_sea['ubicacion']
                                    if resultado_sea.get('inversion') and not proyecto.get('inversion'):
                                        proyecto['inversion'] = resultado_sea['inversion']
                                else:
                                    logger.info(f"⚠️ No se pudo extraer resumen del SEA")
                        except Exception as e:
                            logger.warning(f"⚠️ Error extrayendo resumen del SEA: {e}")
                    
                    # SEGUNDO: Si no se extrajo resumen del SEA, mejorar con el generador
                    if not resumen_extraido and sea_resumen_generador:
                        try:
                            # Generar un resumen mejorado basado en la información disponible
                            resumen_mejorado = sea_resumen_generador.mejorar_resumen(proyecto)
                            if resumen_mejorado:
                                proyecto['resumen'] = resumen_mejorado
                                logger.info(f"📝 Resumen mejorado con generador para {proyecto['titulo'][:30]}")
                        except Exception as e:
                            logger.warning(f"⚠️ No se pudo mejorar resumen: {e}")
                    
                    # Si no hay resumen, crear uno básico
                    if not proyecto.get('resumen'):
                        # Crear resumen básico con la información disponible
                        titulo_lower = proyecto.get('titulo', '').lower()
                        
                        if 'fotovoltaico' in titulo_lower or 'solar' in titulo_lower:
                            resumen_basico = f"Proyecto de generación de energía solar fotovoltaica"
                        elif 'eólico' in titulo_lower:
                            resumen_basico = f"Proyecto de generación de energía eólica"
                        else:
                            resumen_basico = f"{proyecto.get('tipo', 'Proyecto')} presentado"
                        
                        if proyecto.get('empresa') or proyecto.get('titular'):
                            resumen_basico += f" por {proyecto.get('empresa') or proyecto.get('titular')}"
                        if proyecto.get('region'):
                            resumen_basico += f" en {proyecto['region']}"
                        if proyecto.get('comuna'):
                            resumen_basico += f", comuna de {proyecto['comuna']}"
                        if proyecto.get('inversion'):
                            resumen_basico += f". Inversión estimada: {proyecto['inversion']}"
                        
                        proyecto['resumen'] = resumen_basico
                    
                    # Agregar inversión como campo separado si está en el resumen
                    if 'USD' in proyecto.get('resumen', '') or 'MM' in proyecto.get('resumen', ''):
                        import re
                        # Buscar patrón de inversión en el resumen
                        match = re.search(r'(USD?\s*[\d,.]+(\s*M+|\s*millones)?)', proyecto['resumen'], re.IGNORECASE)
                        if match and not proyecto.get('inversion'):
                            proyecto['inversion'] = match.group(1)
                    
                    resultado['proyectos_sea'].append(proyecto)
                    
        logger.info(f"📊 Formateado para informe: {len(resultado['proyectos_sea'])} proyectos SEA")
        
        return resultado

# Función de test
if __name__ == "__main__":
    logger.info("=== TEST SCRAPER AMBIENTAL INTEGRADO ===")
    scraper = ScraperAmbiental()
    
    datos = scraper.obtener_datos_ambientales(dias_atras=3)
    
    print(f"\n📊 RESULTADOS:")
    print(f"   Proyectos SEA: {len(datos.get('proyectos_sea', []))}")
    
    if datos.get('metadata', {}).get('errores'):
        print(f"\n⚠️ Errores encontrados:")
        for error in datos['metadata']['errores']:
            print(f"   - {error}")