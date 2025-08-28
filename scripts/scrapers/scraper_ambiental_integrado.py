"""
Scraper integrado para datos ambientales (SEA y SMA)
Con telemetría y manejo robusto de errores
Actualizado para usar scrapers web más confiables
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import json
from typing import List, Dict
import random
import time
from scripts.scrapers.telemetria_ambiental import telemetria

# Importar nuevos scrapers más confiables
try:
    # PRIMERO intentar el scraper SELENIUM COMPLETO que SÍ FUNCIONA
    from scripts.scrapers.scraper_sea_selenium_completo import ScraperSEASeleniumCompleto
    from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
    USE_NEW_SCRAPERS = True
    USE_SEA_SELENIUM_COMPLETO = True
    USE_SEA_CORRECTO = False
    USE_SEA_ROBUSTO = False
    USE_SEA_FINAL = False
    USE_SEA_DEFINITIVO = False
    USE_SEIA_BUSQUEDA = False
except ImportError:
    try:
        # Si no está disponible, usar scraper CORRECTO que usa buscarProyectoResumen.php
        from scripts.scrapers.scraper_sea_correcto import ScraperSEACorrecto
        from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
        USE_NEW_SCRAPERS = True
        USE_SEA_SELENIUM_COMPLETO = False
        USE_SEA_CORRECTO = True
        USE_SEA_ROBUSTO = False
        USE_SEA_FINAL = False
        USE_SEA_DEFINITIVO = False
        USE_SEIA_BUSQUEDA = False
    except ImportError:
        try:
            # Si no está disponible, usar scraper FINAL con Selenium
            from scripts.scrapers.scraper_sea_final import ScraperSEAFinal
            from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
            USE_NEW_SCRAPERS = True
            USE_SEA_SELENIUM_COMPLETO = False
            USE_SEA_CORRECTO = False
            USE_SEA_ROBUSTO = False
            USE_SEA_FINAL = True
            USE_SEA_DEFINITIVO = False
            USE_SEIA_BUSQUEDA = False
        except ImportError:
            try:
                # Luego intentar el scraper ROBUSTO
                from scripts.scrapers.scraper_sea_robusto import ScraperSEARobusto
                from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
                USE_NEW_SCRAPERS = True
                USE_SEA_SELENIUM_COMPLETO = False
                USE_SEA_CORRECTO = False
                USE_SEA_ROBUSTO = True
                USE_SEA_FINAL = False
                USE_SEA_DEFINITIVO = False
                USE_SEIA_BUSQUEDA = False
            except ImportError:
                try:
                    # Intentar el scraper definitivo
                    from scripts.scrapers.scraper_sea_definitivo import ScraperSEADefinitivo
                    from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
                    USE_NEW_SCRAPERS = True
                    USE_SEA_SELENIUM_COMPLETO = False
                    USE_SEA_CORRECTO = False
                    USE_SEA_ROBUSTO = False
                    USE_SEA_FINAL = False
                    USE_SEA_DEFINITIVO = True
                    USE_SEIA_BUSQUEDA = False
                except ImportError:
                    try:
                        from scripts.scrapers.scraper_seia_busqueda import ScraperSEIABusqueda
                        from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
                        USE_NEW_SCRAPERS = True
                        USE_SEA_SELENIUM_COMPLETO = False
                        USE_SEA_CORRECTO = False
                        USE_SEA_ROBUSTO = False
                        USE_SEA_FINAL = False
                        USE_SEA_DEFINITIVO = False
                        USE_SEIA_BUSQUEDA = True
                    except ImportError:
                        try:
                            from scripts.scrapers.scraper_sea_simple import ScraperSEASimple
                            from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
                            USE_NEW_SCRAPERS = True
                            USE_SEA_SELENIUM_COMPLETO = False
                            USE_SEA_CORRECTO = False
                            USE_SEA_ROBUSTO = False
                            USE_SEA_FINAL = False
                            USE_SEA_DEFINITIVO = False
                            USE_SEIA_BUSQUEDA = False
                        except ImportError:
                            USE_NEW_SCRAPERS = False
                            USE_SEA_SELENIUM_COMPLETO = False
                            USE_SEA_CORRECTO = False
                            USE_SEA_ROBUSTO = False
                            USE_SEA_FINAL = False
                            USE_SEA_DEFINITIVO = False
                            USE_SEIA_BUSQUEDA = False
                            logger = logging.getLogger(__name__)
                            logger.warning("No se pudieron importar los nuevos scrapers")

logger = logging.getLogger(__name__)

class ScraperAmbiental:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9'
        })
        
        # Inicializar nuevos scrapers si están disponibles
        if USE_NEW_SCRAPERS:
            if USE_SEA_SELENIUM_COMPLETO:
                self.scraper_sea = ScraperSEASeleniumCompleto()
                logger.info("✅ Usando scraper SEA SELENIUM COMPLETO (¡FUNCIONA!)")
            elif USE_SEA_CORRECTO:
                self.scraper_sea = ScraperSEACorrecto()
                logger.info("✅ Usando scraper SEA CORRECTO (buscarProyectoResumen.php)")
            elif USE_SEA_FINAL:
                self.scraper_sea = ScraperSEAFinal()
                logger.info("✅ Usando scraper SEA FINAL con Selenium")
            elif USE_SEA_ROBUSTO:
                self.scraper_sea = ScraperSEARobusto()
                logger.info("✅ Usando scraper SEA ROBUSTO (optimizado)")
            elif USE_SEA_DEFINITIVO:
                self.scraper_sea = ScraperSEADefinitivo()
                logger.info("✅ Usando scraper SEA DEFINITIVO")
            elif USE_SEIA_BUSQUEDA:
                self.scraper_sea = ScraperSEIABusqueda()
                logger.info("✅ Usando scraper SEIA búsqueda para SEA")
            else:
                self.scraper_sea = ScraperSEASimple()
                logger.info("✅ Usando scraper simple para SEA")
            self.scraper_sma = ScraperSNIFAWeb()
            logger.info("✅ Usando scraper web para SMA")
        else:
            self.scraper_sea = None
            self.scraper_sma = None
            logger.info("⚠️ Scrapers no disponibles")
    
    def obtener_datos_ambientales(self, dias_atras: int = 7) -> Dict[str, List[Dict]]:
        """
        Obtiene datos ambientales de SEA y SMA con telemetría
        
        Returns:
            Diccionario con proyectos SEA y sanciones SMA
        """
        inicio = time.time()
        errores_totales = []
        
        # Obtener proyectos SEA
        try:
            inicio_sea = time.time()
            proyectos_sea = self._obtener_proyectos_sea(dias_atras)
            tiempo_sea = (time.time() - inicio_sea) * 1000
            
            # Registrar telemetría SEA
            telemetria.registrar_extraccion('SEA', {
                'total_items': len(proyectos_sea),
                'tiempo_ms': tiempo_sea,
                'exitoso': len(proyectos_sea) > 0,
                'tipo_datos': ['proyectos', 'rca']
            })
        except Exception as e:
            logger.error(f"Error obteniendo datos SEA: {str(e)}")
            proyectos_sea = []
            errores_totales.append(f"SEA: {str(e)}")
            
            telemetria.registrar_extraccion('SEA', {
                'total_items': 0,
                'tiempo_ms': 0,
                'exitoso': False,
                'errores': [str(e)]
            })
        
        # Obtener sanciones SMA
        try:
            inicio_sma = time.time()
            sanciones_sma = self._obtener_sanciones_sma(dias_atras)
            tiempo_sma = (time.time() - inicio_sma) * 1000
            
            # Registrar telemetría SMA
            telemetria.registrar_extraccion('SMA', {
                'total_items': len(sanciones_sma),
                'tiempo_ms': tiempo_sma,
                'exitoso': len(sanciones_sma) > 0,
                'tipo_datos': ['sanciones', 'multas']
            })
        except Exception as e:
            logger.error(f"Error obteniendo datos SMA: {str(e)}")
            sanciones_sma = []
            errores_totales.append(f"SMA: {str(e)}")
            
            telemetria.registrar_extraccion('SMA', {
                'total_items': 0,
                'tiempo_ms': 0,
                'exitoso': False,
                'errores': [str(e)]
            })
        
        tiempo_total = (time.time() - inicio) * 1000
        
        datos = {
            'proyectos_sea': proyectos_sea,
            'sanciones_sma': sanciones_sma,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'tiempo_total_ms': tiempo_total,
                'errores': errores_totales,
                'telemetria': {
                    'sea_items': len(proyectos_sea),
                    'sma_items': len(sanciones_sma),
                    'total_items': len(proyectos_sea) + len(sanciones_sma)
                }
            }
        }
        
        logger.info(f"✅ Datos ambientales obtenidos en {tiempo_total:.0f}ms - SEA: {len(proyectos_sea)}, SMA: {len(sanciones_sma)}")
        
        return datos
    
    def _obtener_proyectos_sea(self, dias_atras: int) -> List[Dict]:
        """
        Obtiene proyectos con RCA del SEA
        Usa el nuevo scraper con Selenium para datos reales
        """
        # Usar nuevo scraper si está disponible
        if USE_NEW_SCRAPERS and self.scraper_sea:
            try:
                logger.info("🔄 Obteniendo proyectos SEA con scraper...")
                proyectos = self.scraper_sea.obtener_datos_sea(dias_atras=dias_atras)
                if proyectos:
                    logger.info(f"✅ Obtenidos {len(proyectos)} proyectos SEA reales")
                    return proyectos
                else:
                    logger.warning("⚠️ No se encontraron proyectos SEA")
                    return []
            except Exception as e:
                logger.error(f"❌ Error con scraper SEA: {str(e)}")
                return []
        
        logger.warning("⚠️ Scraper SEA no disponible")
        return []
    
    def _obtener_sanciones_sma(self, dias_atras: int) -> List[Dict]:
        """
        Obtiene sanciones de la SMA
        Usa el nuevo scraper web para datos reales
        """
        # Usar nuevo scraper si está disponible
        if USE_NEW_SCRAPERS and self.scraper_sma:
            try:
                logger.info("🔄 Obteniendo sanciones SMA con scraper web...")
                sanciones = self.scraper_sma.obtener_datos_sma(dias_atras=dias_atras)
                if sanciones:
                    logger.info(f"✅ Obtenidas {len(sanciones)} sanciones SMA reales")
                    return sanciones
                else:
                    logger.warning("⚠️ No se encontraron sanciones SMA")
                    return []
            except Exception as e:
                logger.error(f"❌ Error con scraper SMA: {str(e)}")
                return []
        
        logger.warning("⚠️ Scraper SMA no disponible")
        return []
    
    def formatear_para_informe(self, datos: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Formatea los datos ambientales para el informe
        """
        # Combinar y ordenar por relevancia
        todos = []
        
        for proyecto in datos.get('proyectos_sea', []):
            todos.append(proyecto)
        
        for sancion in datos.get('sanciones_sma', []):
            todos.append(sancion)
        
        # Ordenar por relevancia
        todos.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
        
        # Separar por categoría para el informe
        resultado = {
            'destacados': todos[:5],  # Los 5 más relevantes
            'proyectos_sea': datos.get('proyectos_sea', []),
            'sanciones_sma': datos.get('sanciones_sma', [])
        }
        
        return resultado


def test_scraper_ambiental():
    """
    Función de prueba del scraper ambiental integrado
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🌍 PRUEBA SCRAPER AMBIENTAL INTEGRADO (SEA + SMA)")
    print("="*70)
    
    scraper = ScraperAmbiental()
    
    # Obtener datos de los últimos 7 días
    print("\n📋 Obteniendo datos ambientales de los últimos 7 días...")
    datos = scraper.obtener_datos_ambientales(dias_atras=7)
    
    # Mostrar proyectos SEA
    print("\n" + "-"*70)
    print("🏗️ PROYECTOS SEA (Resoluciones de Calificación Ambiental)")
    print("-"*70)
    
    for i, proyecto in enumerate(datos['proyectos_sea'], 1):
        print(f"\n{i}. {proyecto['titulo']}")
        print(f"   📅 {proyecto['fecha']} | 🏢 {proyecto['empresa']}")
        print(f"   💰 Inversión: USD {proyecto.get('inversion_mmusd', 0):.1f}MM")
        print(f"   📝 {proyecto['resumen']}")
    
    # Mostrar sanciones SMA
    print("\n" + "-"*70)
    print("⚖️ SANCIONES SMA (Superintendencia del Medio Ambiente)")
    print("-"*70)
    
    for i, sancion in enumerate(datos['sanciones_sma'], 1):
        print(f"\n{i}. {sancion['titulo']}")
        print(f"   📅 {sancion['fecha']} | 🏢 {sancion['empresa']}")
        print(f"   💸 {sancion.get('multa', 'N/A')}")
        print(f"   📝 {sancion['resumen']}")
    
    # Formatear para informe
    print("\n" + "="*70)
    print("📊 DATOS FORMATEADOS PARA INFORME")
    print("="*70)
    
    formateado = scraper.formatear_para_informe(datos)
    
    print("\n⭐ TOP 5 MÁS RELEVANTES:")
    for i, item in enumerate(formateado['destacados'], 1):
        print(f"\n{i}. [{item['fuente']}] {item['titulo']}")
        print(f"   Relevancia: ⭐ {item.get('relevancia', 0):.1f}/10")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA - Datos de ejemplo listos para integración")
    print("="*70)
    print("\nNOTA: Actualmente usando datos de ejemplo. Se actualizará con scraping")
    print("real cuando se confirmen las URLs y estructura de las APIs oficiales.")


if __name__ == "__main__":
    test_scraper_ambiental()