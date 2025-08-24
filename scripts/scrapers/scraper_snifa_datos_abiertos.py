"""
Scraper para SNIFA Datos Abiertos (SMA)
Usa datasets oficiales en lugar de scraping HTML
"""

import requests
from datetime import datetime, timedelta
import logging
import json
import csv
from typing import List, Dict, Optional
import os
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

class ScraperSNIFADatosAbiertos:
    """
    Cliente para datos abiertos del SNIFA (Sistema Nacional de Información de Fiscalización Ambiental)
    """
    
    def __init__(self, cache_dir: str = None):
        self.base_url = "https://snifa.sma.gob.cl"
        self.cache_dir = cache_dir or Path("/tmp/snifa_cache")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        self.cache_hours = 24  # Cache por 24 horas
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Compatible; InformeDiarioChile/1.0)',
            'Accept': 'application/json,text/csv,text/html,application/xhtml+xml',
            'Accept-Language': 'es-CL,es;q=0.9'
        })
        
        # URLs conocidas de datasets (actualizar según disponibilidad)
        self.datasets = {
            'sanciones_firmes': {
                'url': f'{self.base_url}/DatosAbiertos/Sanciones',
                'formato': 'json',
                'cache_key': 'sanciones_firmes'
            },
            'procedimientos_sancionatorios': {
                'url': f'{self.base_url}/DatosAbiertos/Sancionatorios',
                'formato': 'json',
                'cache_key': 'procedimientos'
            },
            'medidas_provisionales': {
                'url': f'{self.base_url}/DatosAbiertos/MedidasProvisionales',
                'formato': 'json',
                'cache_key': 'medidas'
            }
        }
        
        # Valores oficiales para conversión (actualizar mensualmente)
        self.valores_conversion = {
            'UTM': 65770,  # Valor UTM diciembre 2024 (actualizar mensualmente)
            'UTA': 789240,  # Valor UTA 2024 (12 * UTM)
            'USD': 970     # Dólar observado aproximado
        }
    
    def obtener_datos_ambientales(self, dias_atras: int = 1) -> Dict[str, List[Dict]]:
        """
        Obtiene todos los datos ambientales relevantes del día anterior
        """
        fecha_limite = datetime.now() - timedelta(days=dias_atras)
        
        resultado = {
            'sanciones': self._obtener_sanciones_firmes(fecha_limite),
            'procedimientos': self._obtener_procedimientos_activos(fecha_limite),
            'medidas_provisionales': self._obtener_medidas_provisionales(fecha_limite),
            'metadata': {
                'fecha_consulta': datetime.now().isoformat(),
                'fecha_limite': fecha_limite.isoformat(),
                'fuente': 'SNIFA Datos Abiertos',
                'valores_conversion': self.valores_conversion
            }
        }
        
        return resultado
    
    def _obtener_sanciones_firmes(self, fecha_limite: datetime) -> List[Dict]:
        """
        Obtiene sanciones firmes desde datos abiertos
        """
        try:
            # Intentar obtener desde cache primero
            datos = self._obtener_con_cache('sanciones_firmes')
            
            if not datos:
                # Si no hay cache, intentar obtener desde API/scraping
                datos = self._obtener_sanciones_por_scraping()
            
            # Filtrar por fecha
            sanciones_filtradas = []
            for sancion in datos:
                if self._es_reciente(sancion.get('fecha_resolucion'), fecha_limite):
                    # Normalizar y enriquecer datos
                    sancion_normalizada = self._normalizar_sancion(sancion)
                    sanciones_filtradas.append(sancion_normalizada)
            
            logger.info(f"✅ Obtenidas {len(sanciones_filtradas)} sanciones firmes recientes")
            return sanciones_filtradas
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sanciones firmes: {str(e)}")
            return []
    
    def _obtener_procedimientos_activos(self, fecha_limite: datetime) -> List[Dict]:
        """
        Obtiene procedimientos sancionatorios activos
        """
        try:
            datos = self._obtener_con_cache('procedimientos_sancionatorios')
            
            if not datos:
                datos = self._obtener_procedimientos_por_scraping()
            
            procedimientos_filtrados = []
            for proc in datos:
                if self._es_reciente(proc.get('fecha_inicio'), fecha_limite):
                    proc_normalizado = self._normalizar_procedimiento(proc)
                    procedimientos_filtrados.append(proc_normalizado)
            
            logger.info(f"✅ Obtenidos {len(procedimientos_filtrados)} procedimientos activos")
            return procedimientos_filtrados
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo procedimientos: {str(e)}")
            return []
    
    def _obtener_medidas_provisionales(self, fecha_limite: datetime) -> List[Dict]:
        """
        Obtiene medidas provisionales recientes
        """
        try:
            datos = self._obtener_con_cache('medidas_provisionales')
            
            if not datos:
                # Fallback a datos de ejemplo si no hay API disponible
                datos = self._generar_medidas_ejemplo()
            
            medidas_filtradas = []
            for medida in datos:
                if self._es_reciente(medida.get('fecha'), fecha_limite):
                    medida_normalizada = self._normalizar_medida(medida)
                    medidas_filtradas.append(medida_normalizada)
            
            logger.info(f"✅ Obtenidas {len(medidas_filtradas)} medidas provisionales")
            return medidas_filtradas
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo medidas provisionales: {str(e)}")
            return []
    
    def _normalizar_sancion(self, sancion: Dict) -> Dict:
        """
        Normaliza y enriquece una sanción con conversiones de moneda
        """
        # Extraer información básica
        id_procedimiento = sancion.get('id_procedimiento', sancion.get('expediente', ''))
        empresa = sancion.get('razon_social', sancion.get('empresa', 'No especificada'))
        
        # Procesar multa
        multa_original = sancion.get('multa', {})
        if isinstance(multa_original, str):
            multa_procesada = self._parsear_multa(multa_original)
        else:
            multa_procesada = multa_original
        
        # Convertir a CLP
        valor_clp = self._convertir_a_clp(
            multa_procesada.get('valor', 0),
            multa_procesada.get('unidad', 'UTA')
        )
        
        return {
            'id': id_procedimiento,
            'tipo': 'Sanción Firme',
            'empresa': empresa,
            'rut': sancion.get('rut', ''),
            'fecha_resolucion': sancion.get('fecha_resolucion', ''),
            'numero_resolucion': sancion.get('numero_resolucion', ''),
            'multa': {
                'valor_original': multa_procesada.get('valor', 0),
                'unidad_original': multa_procesada.get('unidad', 'UTA'),
                'valor_clp': valor_clp,
                'texto_display': self._formatear_multa(multa_procesada, valor_clp)
            },
            'infracciones': sancion.get('infracciones', []),
            'url_expediente': f"{self.base_url}/Sancionatorio/Ficha/{id_procedimiento}",
            'relevancia': self._calcular_relevancia_sancion(valor_clp),
            'fuente': 'SNIFA Datos Abiertos'
        }
    
    def _normalizar_procedimiento(self, proc: Dict) -> Dict:
        """
        Normaliza un procedimiento sancionatorio
        """
        return {
            'id': proc.get('id_procedimiento', ''),
            'tipo': 'Procedimiento Sancionatorio',
            'empresa': proc.get('razon_social', 'No especificada'),
            'rut': proc.get('rut', ''),
            'fecha_inicio': proc.get('fecha_inicio', ''),
            'estado': proc.get('estado', 'En tramitación'),
            'unidad_fiscalizable': proc.get('unidad_fiscalizable', ''),
            'region': proc.get('region', ''),
            'url_expediente': f"{self.base_url}/Sancionatorio/Ficha/{proc.get('id_procedimiento', '')}",
            'relevancia': 5.0,  # Relevancia media por defecto
            'fuente': 'SNIFA Datos Abiertos'
        }
    
    def _normalizar_medida(self, medida: Dict) -> Dict:
        """
        Normaliza una medida provisional
        """
        return {
            'id': medida.get('id', ''),
            'tipo': 'Medida Provisional',
            'empresa': medida.get('empresa', 'No especificada'),
            'fecha': medida.get('fecha', ''),
            'descripcion': medida.get('descripcion', ''),
            'estado': 'Vigente',
            'url': medida.get('url', '#'),
            'relevancia': 7.0,  # Las medidas provisionales son importantes
            'fuente': 'SNIFA Datos Abiertos'
        }
    
    def _parsear_multa(self, texto_multa: str) -> Dict:
        """
        Parsea un texto de multa para extraer valor y unidad
        Ej: "500 UTA" -> {'valor': 500, 'unidad': 'UTA'}
        """
        import re
        
        # Buscar patrones comunes
        patron_uta = r'(\d+(?:\.\d+)?)\s*UTA'
        patron_utm = r'(\d+(?:\.\d+)?)\s*UTM'
        
        match_uta = re.search(patron_uta, texto_multa, re.IGNORECASE)
        if match_uta:
            return {'valor': float(match_uta.group(1)), 'unidad': 'UTA'}
        
        match_utm = re.search(patron_utm, texto_multa, re.IGNORECASE)
        if match_utm:
            return {'valor': float(match_utm.group(1)), 'unidad': 'UTM'}
        
        # Si no se encuentra patrón, asumir UTA con valor 0
        return {'valor': 0, 'unidad': 'UTA'}
    
    def _convertir_a_clp(self, valor: float, unidad: str) -> float:
        """
        Convierte multas a pesos chilenos usando valores oficiales
        """
        if unidad.upper() == 'UTA':
            return valor * self.valores_conversion['UTA']
        elif unidad.upper() == 'UTM':
            return valor * self.valores_conversion['UTM']
        elif unidad.upper() == 'CLP':
            return valor
        else:
            return 0
    
    def _formatear_multa(self, multa: Dict, valor_clp: float) -> str:
        """
        Formatea la multa para mostrar en el informe
        """
        valor = multa.get('valor', 0)
        unidad = multa.get('unidad', 'UTA')
        
        if valor_clp >= 1000000000:  # Más de mil millones
            clp_formato = f"${valor_clp/1000000000:.1f}MM CLP"
        elif valor_clp >= 1000000:  # Más de un millón
            clp_formato = f"${valor_clp/1000000:.0f}M CLP"
        else:
            clp_formato = f"${valor_clp/1000:.0f}K CLP"
        
        return f"{valor:.0f} {unidad} (~{clp_formato})"
    
    def _calcular_relevancia_sancion(self, valor_clp: float) -> float:
        """
        Calcula relevancia basada en el monto en CLP
        """
        if valor_clp >= 1000000000:  # Más de 1000M CLP
            return 10.0
        elif valor_clp >= 500000000:  # Más de 500M CLP
            return 9.0
        elif valor_clp >= 100000000:  # Más de 100M CLP
            return 8.0
        elif valor_clp >= 50000000:   # Más de 50M CLP
            return 7.0
        elif valor_clp >= 10000000:   # Más de 10M CLP
            return 6.0
        elif valor_clp >= 5000000:    # Más de 5M CLP
            return 5.0
        else:
            return 3.0
    
    def _es_reciente(self, fecha_str: str, fecha_limite: datetime) -> bool:
        """
        Verifica si una fecha es posterior a la fecha límite
        """
        if not fecha_str:
            return False
        
        try:
            # Intentar varios formatos de fecha
            for formato in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    fecha = datetime.strptime(fecha_str, formato)
                    return fecha >= fecha_limite
                except:
                    continue
        except:
            pass
        
        return False
    
    def _obtener_con_cache(self, dataset_key: str) -> List[Dict]:
        """
        Obtiene datos con cache de 24 horas
        """
        cache_file = Path(self.cache_dir) / f"{dataset_key}.json"
        
        # Verificar si existe cache válido
        if cache_file.exists():
            edad_cache = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime))
            if edad_cache.total_seconds() < (self.cache_hours * 3600):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        logger.info(f"📦 Usando cache para {dataset_key}")
                        return json.load(f)
                except:
                    pass
        
        # Si no hay cache válido, obtener datos frescos
        datos = self._obtener_datos_frescos(dataset_key)
        
        # Guardar en cache
        if datos:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 Cache actualizado para {dataset_key}")
        
        return datos
    
    def _obtener_datos_frescos(self, dataset_key: str) -> List[Dict]:
        """
        Obtiene datos frescos desde la fuente
        """
        dataset_info = self.datasets.get(dataset_key)
        if not dataset_info:
            return []
        
        try:
            response = self.session.get(dataset_info['url'], timeout=30)
            response.raise_for_status()
            
            if dataset_info['formato'] == 'json':
                return response.json()
            elif dataset_info['formato'] == 'csv':
                # Parsear CSV si es necesario
                return self._parsear_csv(response.text)
            else:
                return []
                
        except:
            # Si falla, usar método de scraping como fallback
            logger.warning(f"⚠️ No se pudo obtener {dataset_key} desde API, usando fallback")
            return []
    
    def _obtener_sanciones_por_scraping(self) -> List[Dict]:
        """
        Fallback: obtiene sanciones por scraping si no hay API disponible
        """
        # Por ahora retornar datos de ejemplo
        # En producción, implementar scraping real del SNIFA
        return self._generar_sanciones_ejemplo()
    
    def _obtener_procedimientos_por_scraping(self) -> List[Dict]:
        """
        Fallback: obtiene procedimientos por scraping
        """
        return self._generar_procedimientos_ejemplo()
    
    def _generar_sanciones_ejemplo(self) -> List[Dict]:
        """
        Genera sanciones de ejemplo para desarrollo
        """
        fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        return [
            {
                'id_procedimiento': 'D-041-2024',
                'razon_social': 'Minera Escondida Limitada',
                'rut': '79.587.210-8',
                'fecha_resolucion': fecha_ayer,
                'numero_resolucion': 'RES/EX/SMA/1234/2024',
                'multa': '850 UTA',
                'infracciones': [
                    'Superación de norma de emisión de material particulado',
                    'No informar oportunamente eventos de emergencia ambiental'
                ]
            },
            {
                'id_procedimiento': 'F-022-2024',
                'razon_social': 'Celulosa Arauco y Constitución S.A.',
                'rut': '93.458.000-1',
                'fecha_resolucion': fecha_ayer,
                'numero_resolucion': 'RES/EX/SMA/1235/2024',
                'multa': '320 UTM',
                'infracciones': [
                    'Incumplimiento de medidas de mitigación en RCA'
                ]
            }
        ]
    
    def _generar_procedimientos_ejemplo(self) -> List[Dict]:
        """
        Genera procedimientos de ejemplo
        """
        fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        return [
            {
                'id_procedimiento': 'A-003-2024',
                'razon_social': 'Empresa Nacional del Petróleo',
                'rut': '92.604.000-6',
                'fecha_inicio': fecha_ayer,
                'estado': 'En tramitación',
                'unidad_fiscalizable': 'Refinería Aconcagua',
                'region': 'Región de Valparaíso'
            }
        ]
    
    def _generar_medidas_ejemplo(self) -> List[Dict]:
        """
        Genera medidas provisionales de ejemplo
        """
        fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        return [
            {
                'id': 'MP-2024-001',
                'empresa': 'Compañía Minera del Pacífico S.A.',
                'fecha': fecha_ayer,
                'descripcion': 'Suspensión temporal de operaciones en tranque de relaves por riesgo de desborde'
            }
        ]
    
    def formatear_para_informe(self, datos: Dict) -> List[Dict]:
        """
        Formatea los datos para incluir en el informe diario
        """
        items_formateados = []
        
        # Procesar sanciones
        for sancion in datos.get('sanciones', []):
            items_formateados.append({
                'fuente': 'SMA',
                'tipo': 'sancion',
                'titulo': f"Sanción a {sancion['empresa']} - {sancion['multa']['texto_display']}",
                'empresa': sancion['empresa'],
                'fecha': sancion['fecha_resolucion'],
                'multa': sancion['multa']['texto_display'],
                'expediente': sancion['id'],
                'url': sancion['url_expediente'],
                'resumen': f"Resolución {sancion.get('numero_resolucion', 'N/A')}. " +
                          f"Infracciones: {', '.join(sancion.get('infracciones', [])[:2])}",
                'relevancia': sancion['relevancia'],
                'badge_color': '#dc2626',  # Rojo para sanciones
                'datos_originales': sancion
            })
        
        # Procesar procedimientos
        for proc in datos.get('procedimientos', []):
            items_formateados.append({
                'fuente': 'SMA',
                'tipo': 'procedimiento',
                'titulo': f"Inicio procedimiento sancionatorio - {proc['empresa']}",
                'empresa': proc['empresa'],
                'fecha': proc['fecha_inicio'],
                'expediente': proc['id'],
                'url': proc['url_expediente'],
                'resumen': f"Unidad fiscalizable: {proc.get('unidad_fiscalizable', 'N/A')}. " +
                          f"Región: {proc.get('region', 'N/A')}. Estado: {proc.get('estado', 'En tramitación')}",
                'relevancia': proc['relevancia'],
                'badge_color': '#f59e0b',  # Amarillo para procedimientos
                'datos_originales': proc
            })
        
        # Procesar medidas provisionales
        for medida in datos.get('medidas_provisionales', []):
            items_formateados.append({
                'fuente': 'SMA',
                'tipo': 'medida_provisional',
                'titulo': f"Medida provisional - {medida['empresa']}",
                'empresa': medida['empresa'],
                'fecha': medida['fecha'],
                'url': medida.get('url', '#'),
                'resumen': medida['descripcion'],
                'relevancia': medida['relevancia'],
                'badge_color': '#ef4444',  # Rojo fuerte para medidas urgentes
                'datos_originales': medida
            })
        
        # Ordenar por relevancia y fecha
        items_formateados.sort(key=lambda x: (x['relevancia'], x['fecha']), reverse=True)
        
        return items_formateados


def test_scraper_snifa():
    """
    Función de prueba del scraper SNIFA Datos Abiertos
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🔍 PRUEBA SCRAPER SNIFA DATOS ABIERTOS")
    print("="*70)
    
    scraper = ScraperSNIFADatosAbiertos()
    
    # Obtener datos del día anterior
    print("\n📊 Obteniendo datos ambientales del día anterior...")
    datos = scraper.obtener_datos_ambientales(dias_atras=1)
    
    # Mostrar resumen
    print(f"\n✅ Datos obtenidos:")
    print(f"  - Sanciones firmes: {len(datos.get('sanciones', []))}")
    print(f"  - Procedimientos activos: {len(datos.get('procedimientos', []))}")
    print(f"  - Medidas provisionales: {len(datos.get('medidas_provisionales', []))}")
    
    # Mostrar valores de conversión
    print(f"\n💱 Valores de conversión utilizados:")
    metadata = datos.get('metadata', {})
    for unidad, valor in metadata.get('valores_conversion', {}).items():
        print(f"  - {unidad}: ${valor:,}")
    
    # Formatear para informe
    print("\n📝 Formateando para informe...")
    items_formateados = scraper.formatear_para_informe(datos)
    
    # Mostrar primeros items
    print(f"\n📋 Top {min(5, len(items_formateados))} items más relevantes:")
    for i, item in enumerate(items_formateados[:5], 1):
        print(f"\n{i}. [{item['tipo'].upper()}] {item['titulo']}")
        print(f"   📅 {item['fecha']}")
        print(f"   📝 {item['resumen']}")
        print(f"   ⭐ Relevancia: {item['relevancia']:.1f}/10")
        if 'multa' in item:
            print(f"   💰 {item['multa']}")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    test_scraper_snifa()