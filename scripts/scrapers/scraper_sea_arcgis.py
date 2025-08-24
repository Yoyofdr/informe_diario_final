"""
Scraper para SEA/SEIA usando ArcGIS REST API
Acceso público sin autenticación a proyectos del SEIA
"""

import requests
import json
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from urllib.parse import urlencode
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suprimir warnings de SSL temporalmente
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

logger = logging.getLogger(__name__)

class ScraperSEAArcGIS:
    def __init__(self):
        """
        Inicializa el scraper con endpoints públicos de SEA ArcGIS
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Endpoints públicos del SEA ArcGIS - Usar servidor estable
        self.base_url = "https://arcgis.sea.gob.cl/seamapas/rest/services"
        
        # Capas principales del MapServer
        self.layers = {
            'eia': {
                'id': 1,
                'nombre': 'Estudios de Impacto Ambiental (EIA)',
                'servicio': 'WEBServices/ProyectosSEIA/MapServer'
            },
            'dia': {
                'id': 2,
                'nombre': 'Declaraciones de Impacto Ambiental (DIA)',
                'servicio': 'WEBServices/ProyectosSEIA/MapServer'
            },
            'proyectos': {
                'id': 0,
                'nombre': 'Todos los Proyectos',
                'servicio': 'WEBServices/ProyectosSEIA/MapServer'
            }
        }
        
        # Estados relevantes para filtrar
        self.estados_relevantes = [
            'Aprobado',
            'Rechazado',
            'No admitido a tramitación',
            'En calificación',
            'Término anticipado'
        ]
        
        # Campos a solicitar
        self.campos_proyecto = [
            'OBJECTID',
            'NOMBRE',
            'TITULAR',
            'TIPO_PROYECTO',
            'FECHA_INGRESO',
            'FECHA_PUBLICACION',
            'ESTADO',
            'REGION',
            'COMUNA',
            'INVERSION_ESTIMADA',
            'TIPO_DOCUMENTO',
            'DESCRIPCION',
            'URL_PROYECTO'
        ]
    
    def consultar_capa(self, layer_key: str, where_clause: str = "1=1", 
                      out_fields: str = "*", order_by: str = None) -> Optional[Dict]:
        """
        Consulta una capa específica del servicio ArcGIS
        """
        if layer_key not in self.layers:
            logger.error(f"Capa desconocida: {layer_key}")
            return None
        
        layer_info = self.layers[layer_key]
        url = f"{self.base_url}/{layer_info['servicio']}/{layer_info['id']}/query"
        
        # Parámetros de la consulta
        params = {
            'where': where_clause,
            'outFields': out_fields,
            'f': 'json',
            'returnGeometry': 'false',
            'returnDistinctValues': 'false',
            'returnCountOnly': 'false'
        }
        
        if order_by:
            params['orderByFields'] = order_by
        
        try:
            logger.info(f"🔍 Consultando {layer_info['nombre']}...")
            # Temporalmente deshabilitar verificación SSL debido a certificado expirado del servidor
            response = self.session.get(url, params=params, timeout=30, verify=False)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Error en respuesta ArcGIS: {data['error']}")
                return None
            
            logger.info(f"✅ Obtenidos {len(data.get('features', []))} registros")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error consultando capa {layer_key}: {str(e)}")
            return None
    
    def obtener_proyectos_recientes(self, dias_atras: int = 1) -> List[Dict]:
        """
        Obtiene proyectos publicados en los últimos días
        """
        fecha_desde = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
        
        # Construir consulta WHERE
        # Nota: La sintaxis exacta puede variar según la configuración del servidor
        where_clause = f"FECHA_PUBLICACION >= DATE '{fecha_desde}'"
        
        # Si necesitamos filtrar por estado
        estados_filter = "','".join(self.estados_relevantes)
        where_clause += f" AND ESTADO IN ('{estados_filter}')"
        
        # Obtener campos específicos
        out_fields = ','.join(self.campos_proyecto) if self.campos_proyecto else '*'
        
        # Consultar proyectos
        resultado = self.consultar_capa(
            'proyectos',
            where_clause=where_clause,
            out_fields=out_fields,
            order_by='FECHA_PUBLICACION DESC'
        )
        
        if not resultado or 'features' not in resultado:
            logger.warning("No se obtuvieron proyectos")
            return []
        
        proyectos = []
        for feature in resultado['features']:
            attrs = feature.get('attributes', {})
            
            try:
                # Procesar fecha (timestamp en millisegundos)
                fecha_pub = attrs.get('FECHA_PUBLICACION')
                if fecha_pub:
                    fecha_obj = datetime.fromtimestamp(fecha_pub / 1000)
                    fecha_str = fecha_obj.strftime('%d/%m/%Y')
                else:
                    fecha_str = 'Sin fecha'
                
                # Procesar inversión
                inversion = attrs.get('INVERSION_ESTIMADA', 0)
                if inversion and inversion > 0:
                    if inversion >= 1000:
                        inversion_texto = f"USD ${inversion/1000:.0f}M"
                    else:
                        inversion_texto = f"USD ${inversion:.0f}MM"
                else:
                    inversion_texto = "No especificada"
                
                # Calcular relevancia
                relevancia = self._calcular_relevancia_proyecto(
                    attrs.get('TIPO_DOCUMENTO'),
                    attrs.get('ESTADO'),
                    inversion
                )
                
                proyecto = {
                    'fuente': 'SEA',
                    'tipo': attrs.get('TIPO_DOCUMENTO', 'Proyecto SEIA'),
                    'titulo': attrs.get('NOMBRE', 'Sin nombre'),
                    'titular': attrs.get('TITULAR', 'Sin información'),
                    'fecha': fecha_str,
                    'estado': attrs.get('ESTADO', 'Sin estado'),
                    'region': attrs.get('REGION', 'Sin región'),
                    'comuna': attrs.get('COMUNA', ''),
                    'inversion': inversion_texto,
                    'descripcion': attrs.get('DESCRIPCION', '')[:200] if attrs.get('DESCRIPCION') else '',
                    'relevancia': relevancia,
                    'url': attrs.get('URL_PROYECTO', f"https://seia.sea.gob.cl/expediente/expediente.php?id={attrs.get('OBJECTID')}")
                }
                
                proyectos.append(proyecto)
                
            except Exception as e:
                logger.debug(f"Error procesando proyecto: {str(e)}")
                continue
        
        # Ordenar por relevancia
        proyectos.sort(key=lambda x: x['relevancia'], reverse=True)
        
        logger.info(f"📊 Procesados {len(proyectos)} proyectos del SEA")
        return proyectos
    
    def obtener_estadisticas_periodo(self, dias_atras: int = 30) -> Dict:
        """
        Obtiene estadísticas del período para validación
        """
        fecha_desde = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
        
        stats = {
            'total_proyectos': 0,
            'por_estado': {},
            'por_tipo': {},
            'inversion_total_usd': 0
        }
        
        # Consulta general sin filtro de estado
        where_clause = f"FECHA_PUBLICACION >= DATE '{fecha_desde}'"
        resultado = self.consultar_capa(
            'proyectos',
            where_clause=where_clause,
            out_fields='ESTADO,TIPO_DOCUMENTO,INVERSION_ESTIMADA'
        )
        
        if resultado and 'features' in resultado:
            for feature in resultado['features']:
                attrs = feature.get('attributes', {})
                
                stats['total_proyectos'] += 1
                
                # Por estado
                estado = attrs.get('ESTADO', 'Sin estado')
                stats['por_estado'][estado] = stats['por_estado'].get(estado, 0) + 1
                
                # Por tipo
                tipo = attrs.get('TIPO_DOCUMENTO', 'Sin tipo')
                stats['por_tipo'][tipo] = stats['por_tipo'].get(tipo, 0) + 1
                
                # Inversión total
                inversion = attrs.get('INVERSION_ESTIMADA', 0)
                if inversion and inversion > 0:
                    stats['inversion_total_usd'] += inversion
        
        return stats
    
    def _calcular_relevancia_proyecto(self, tipo: str, estado: str, inversion: float) -> float:
        """
        Calcula relevancia del proyecto basada en tipo, estado e inversión
        """
        relevancia = 5.0
        
        # Por tipo de documento
        if tipo and 'EIA' in tipo:
            relevancia += 2.0  # EIA son más relevantes
        elif tipo and 'DIA' in tipo:
            relevancia += 1.0
        
        # Por estado
        if estado:
            if estado == 'Aprobado':
                relevancia += 2.0
            elif estado == 'Rechazado':
                relevancia += 1.5
            elif estado == 'No admitido a tramitación':
                relevancia += 1.0
            elif estado == 'En calificación':
                relevancia += 0.5
        
        # Por inversión (en millones USD)
        if inversion:
            if inversion >= 1000:  # Más de $1,000M USD
                relevancia += 3.0
            elif inversion >= 500:  # Más de $500M USD
                relevancia += 2.5
            elif inversion >= 100:  # Más de $100M USD
                relevancia += 2.0
            elif inversion >= 50:   # Más de $50M USD
                relevancia += 1.5
            elif inversion >= 10:   # Más de $10M USD
                relevancia += 1.0
        
        return min(relevancia, 10.0)  # Máximo 10
    
    def obtener_datos_sea(self, dias_atras: int = 1) -> List[Dict]:
        """
        Método principal para obtener todos los datos del SEA
        """
        logger.info(f"🌍 Obteniendo datos del SEA (últimos {dias_atras} días)...")
        
        # Obtener proyectos recientes
        proyectos = self.obtener_proyectos_recientes(dias_atras)
        
        # Obtener estadísticas para validación
        if dias_atras <= 7:
            stats = self.obtener_estadisticas_periodo(30)
            logger.info(f"📊 Estadísticas últimos 30 días: {stats['total_proyectos']} proyectos totales")
            logger.info(f"   Por estado: {stats['por_estado']}")
        
        return proyectos


def test_sea_arcgis():
    """
    Prueba el scraper SEA con ArcGIS REST API
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🌍 PRUEBA SCRAPER SEA - ARCGIS REST API")
    print("="*70)
    
    scraper = ScraperSEAArcGIS()
    
    # Probar conexión básica
    print("\n1. Probando conexión con ArcGIS...")
    test_result = scraper.consultar_capa('proyectos', where_clause="1=1", out_fields="OBJECTID")
    if test_result:
        print("✅ Conexión exitosa con ArcGIS")
    else:
        print("❌ No se pudo conectar con ArcGIS")
        return
    
    # Obtener proyectos recientes
    print("\n2. Obteniendo proyectos de los últimos 7 días...")
    proyectos = scraper.obtener_datos_sea(dias_atras=7)
    
    if proyectos:
        print(f"\n✅ Obtenidos {len(proyectos)} proyectos del SEA")
        
        print("\n" + "-"*70)
        print("📋 ÚLTIMOS PROYECTOS SEIA")
        print("-"*70)
        
        for i, proyecto in enumerate(proyectos[:5], 1):
            print(f"\n{i}. {proyecto['titulo']}")
            print(f"   📅 {proyecto['fecha']} | 🏢 {proyecto['titular']}")
            print(f"   📍 {proyecto['region']} - {proyecto['comuna']}")
            print(f"   💰 {proyecto['inversion']}")
            print(f"   📊 Estado: {proyecto['estado']}")
            print(f"   📝 {proyecto['tipo']}")
            if proyecto['descripcion']:
                print(f"   💬 {proyecto['descripcion'][:100]}...")
            print(f"   ⭐ Relevancia: {proyecto['relevancia']:.1f}/10")
    else:
        print("\n⚠️ No se obtuvieron proyectos en los últimos 7 días")
        print("Intentando con últimos 30 días...")
        
        proyectos = scraper.obtener_datos_sea(dias_atras=30)
        if proyectos:
            print(f"\n✅ Obtenidos {len(proyectos)} proyectos en los últimos 30 días")
            for i, proyecto in enumerate(proyectos[:3], 1):
                print(f"\n{i}. {proyecto['titulo']} ({proyecto['fecha']})")
    
    # Obtener estadísticas
    print("\n3. Obteniendo estadísticas del último mes...")
    stats = scraper.obtener_estadisticas_periodo(30)
    print(f"\n📊 Estadísticas últimos 30 días:")
    print(f"   Total proyectos: {stats['total_proyectos']}")
    print(f"   Por estado: {stats['por_estado']}")
    print(f"   Por tipo: {stats['por_tipo']}")
    if stats['inversion_total_usd'] > 0:
        print(f"   Inversión total: USD ${stats['inversion_total_usd']/1000:.0f}M")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    test_sea_arcgis()