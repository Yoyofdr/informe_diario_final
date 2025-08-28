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
    from scraper_sea_selenium_completo import ScraperSEASeleniumCompleto
    logger.info("✅ Importado ScraperSEASeleniumCompleto")
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
                        'empresa': p.get('titular', ''),
                        'inversion': p.get('inversion', ''),
                        'fecha': p.get('fecha_presentacion', ''),
                        'resumen': p.get('resumen', '')
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
        """
        resultado = {
            'proyectos_sea': []
        }
        
        # Formatear proyectos SEA reales
        if datos_ambientales.get('proyectos_sea'):
            for proyecto in datos_ambientales['proyectos_sea']:
                # Solo incluir si tiene título (es un proyecto real)
                if proyecto.get('titulo'):
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