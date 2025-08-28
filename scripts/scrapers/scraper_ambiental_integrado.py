#!/usr/bin/env python3
"""
Scraper integrado para datos ambientales (SEA y SMA)
Usa scrapers especializados para cada fuente
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
    from scripts.scrapers.scraper_sea_selenium_completo import ScraperSEASeleniumCompleto
    logger.info("✅ Importado ScraperSEASeleniumCompleto")
except ImportError as e:
    logger.error(f"❌ Error importando ScraperSEASeleniumCompleto: {e}")
    ScraperSEASeleniumCompleto = None

try:
    from scripts.scrapers.scraper_snifa_web import ScraperSNIFAWeb
    logger.info("✅ Importado ScraperSNIFAWeb")
except ImportError as e:
    logger.error(f"❌ Error importando ScraperSNIFAWeb: {e}")
    ScraperSNIFAWeb = None

# Importar telemetría
try:
    from scripts.scrapers.telemetria import TelemetriaScrapers
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
        
        # Inicializar scrapers
        if ScraperSEASeleniumCompleto:
            self.scraper_sea = ScraperSEASeleniumCompleto()
            logger.info("✅ Scraper SEA con Selenium inicializado")
        else:
            self.scraper_sea = None
            logger.error("❌ Scraper SEA no disponible")
            
        if ScraperSNIFAWeb:
            self.scraper_sma = ScraperSNIFAWeb()
            logger.info("✅ Scraper SMA/SNIFA inicializado")
        else:
            self.scraper_sma = None
            logger.error("❌ Scraper SMA no disponible")
    
    def obtener_datos_ambientales(self, dias_atras: int = 7) -> Dict:
        """
        Obtiene datos ambientales de SEA y SMA
        
        Args:
            dias_atras: Número de días hacia atrás para buscar
            
        Returns:
            Diccionario con proyectos SEA y sanciones SMA
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
        
        # Obtener sanciones SMA
        sanciones_sma = []
        if self.scraper_sma:
            try:
                logger.info("📋 Obteniendo sanciones SMA...")
                sanciones_sma = self._obtener_sanciones_sma(dias_atras)
                
                if telemetria:
                    telemetria.registrar_extraccion('SMA', {
                        'total_items': len(sanciones_sma),
                        'tiempo_ms': (time.time() - inicio) * 1000,
                        'exitoso': True
                    })
                    
                if sanciones_sma:
                    logger.info(f"✅ {len(sanciones_sma)} sanciones SMA encontradas")
                else:
                    logger.warning("⚠️ No se encontraron sanciones SMA")
                    errores_totales.append("SMA: No se encontraron sanciones")
                    
            except Exception as e:
                logger.error(f"❌ Error obteniendo datos SMA: {str(e)}")
                errores_totales.append(f"SMA: {str(e)}")
                
                if telemetria:
                    telemetria.registrar_extraccion('SMA', {
                        'total_items': 0,
                        'tiempo_ms': (time.time() - inicio) * 1000,
                        'exitoso': False,
                        'errores': [str(e)]
                    })
        else:
            logger.warning("⚠️ Scraper SMA no disponible")
            errores_totales.append("SMA: Scraper no disponible")
        
        tiempo_total = (time.time() - inicio) * 1000
        
        # Si hay errores, registrarlos
        if errores_totales:
            logger.error(f"❌ Errores registrados: {errores_totales}")
        
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
    
    def _obtener_sanciones_sma(self, dias_atras: int) -> List[Dict]:
        """
        Obtiene sanciones del SMA/SNIFA
        """
        try:
            logger.info(f"🔄 Obteniendo sanciones SMA de los últimos {dias_atras} días...")
            sanciones = self.scraper_sma.obtener_sanciones(dias_atras=dias_atras)
            
            if sanciones:
                logger.info(f"✅ {len(sanciones)} sanciones SMA obtenidas")
                # Formatear para el informe
                sanciones_formateadas = []
                for s in sanciones:
                    sancion = {
                        'fuente': 'SMA',
                        'fecha_extraccion': datetime.now().isoformat(),
                        'titulo': s.get('razon_social', ''),
                        'url': s.get('url', ''),
                        'expediente': s.get('expediente', ''),
                        'tipo_sancion': s.get('tipo_sancion', ''),
                        'estado': s.get('estado', ''),
                        'comuna': s.get('comuna', ''),
                        'region': s.get('region', ''),
                        'fecha': s.get('fecha_expediente', ''),
                        'resumen': s.get('resumen', '')
                    }
                    sanciones_formateadas.append(sancion)
                return sanciones_formateadas
            else:
                logger.warning("⚠️ No se encontraron sanciones SMA")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error en _obtener_sanciones_sma: {str(e)}")
            raise
    
    def formatear_para_informe(self, datos_ambientales: Dict) -> Dict:
        """
        Formatea los datos ambientales para el informe HTML
        Solo usa datos REALES obtenidos de los scrapers
        """
        resultado = {
            'proyectos_sea': [],
            'sanciones_sma': []
        }
        
        # Formatear proyectos SEA reales
        if datos_ambientales.get('proyectos_sea'):
            for proyecto in datos_ambientales['proyectos_sea']:
                # Solo incluir si tiene título (es un proyecto real)
                if proyecto.get('titulo'):
                    resultado['proyectos_sea'].append(proyecto)
                    
        # Formatear sanciones SMA reales  
        if datos_ambientales.get('sanciones_sma'):
            for sancion in datos_ambientales['sanciones_sma']:
                # Solo incluir si tiene título o expediente (es una sanción real)
                if sancion.get('titulo') or sancion.get('expediente'):
                    resultado['sanciones_sma'].append(sancion)
                    
        logger.info(f"📊 Formateado para informe: {len(resultado['proyectos_sea'])} proyectos SEA, {len(resultado['sanciones_sma'])} sanciones SMA")
        
        return resultado

# Función de test
if __name__ == "__main__":
    logger.info("=== TEST SCRAPER AMBIENTAL INTEGRADO ===")
    scraper = ScraperAmbiental()
    
    datos = scraper.obtener_datos_ambientales(dias_atras=3)
    
    print(f"\n📊 RESULTADOS:")
    print(f"   Proyectos SEA: {len(datos.get('proyectos_sea', []))}")
    print(f"   Sanciones SMA: {len(datos.get('sanciones_sma', []))}")
    
    if datos.get('metadata', {}).get('errores'):
        print(f"\n⚠️ Errores encontrados:")
        for error in datos['metadata']['errores']:
            print(f"   - {error}")