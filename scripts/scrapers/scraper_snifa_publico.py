"""
Scraper para SNIFA Datos Abiertos - Archivos públicos CSV/Excel
Descarga directa desde Google Drive sin autenticación
"""

import requests
import pandas as pd
import io
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class ScraperSNIFAPublico:
    def __init__(self):
        """
        Inicializa el scraper con URLs públicas de SNIFA
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # URLs públicas de Google Drive - SNIFA Datos Abiertos
        # Estos IDs son de los archivos públicos compartidos por SNIFA
        self.fuentes_datos = {
            'sanciones_firmes': {
                'nombre': 'Sanciones Firmes',
                'url_directa': 'https://docs.google.com/spreadsheets/d/1vN_JI_IqYgPqE2m8TlPOZK5a2_GQDcXB/export?format=xlsx',
                'formato': 'excel'
            },
            'procedimientos_sancionatorios': {
                'nombre': 'Procedimientos Sancionatorios',
                'url_directa': 'https://snifa.sma.gob.cl/DatosAbiertos/Docs/ProcedimientosSancionatorios.csv',
                'formato': 'csv'
            },
            'medidas_provisionales': {
                'nombre': 'Medidas Provisionales',
                'url_directa': 'https://snifa.sma.gob.cl/DatosAbiertos/Docs/MedidasProvisionales.csv',
                'formato': 'csv'
            }
        }
        
        # Valores de conversión actualizados
        self.valores_conversion = {
            'UTM': 65770,  # Valor UTM diciembre 2024
            'UTA': 789240,  # Valor UTA 2024 (12 * UTM)
            'USD': 970     # Aproximado
        }
    
    def descargar_datos_publicos(self, fuente: str) -> Optional[pd.DataFrame]:
        """
        Descarga datos públicos desde las fuentes oficiales
        """
        if fuente not in self.fuentes_datos:
            logger.error(f"Fuente desconocida: {fuente}")
            return None
        
        info = self.fuentes_datos[fuente]
        logger.info(f"📥 Descargando {info['nombre']} desde fuente pública...")
        
        try:
            response = self.session.get(info['url_directa'], timeout=30)
            response.raise_for_status()
            
            # Parsear según formato
            if info['formato'] == 'csv':
                df = pd.read_csv(io.StringIO(response.text), encoding='utf-8')
            elif info['formato'] == 'excel':
                df = pd.read_excel(io.BytesIO(response.content))
            else:
                logger.error(f"Formato no soportado: {info['formato']}")
                return None
            
            logger.info(f"✅ Descargados {len(df)} registros de {info['nombre']}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error descargando {info['nombre']}: {str(e)}")
            # Intentar fuente alternativa desde SNIFA directo
            return self._intentar_fuente_alternativa(fuente)
    
    def _intentar_fuente_alternativa(self, fuente: str) -> Optional[pd.DataFrame]:
        """
        Intenta descargar desde fuente alternativa (SNIFA directo)
        """
        urls_alternativas = {
            'sanciones_firmes': 'https://snifa.sma.gob.cl/DatosAbiertos/Capa/45',
            'procedimientos_sancionatorios': 'https://snifa.sma.gob.cl/DatosAbiertos/Capa/46',
            'medidas_provisionales': 'https://snifa.sma.gob.cl/DatosAbiertos/Capa/47'
        }
        
        if fuente not in urls_alternativas:
            return None
        
        try:
            logger.info(f"🔄 Intentando fuente alternativa para {fuente}...")
            url = urls_alternativas[fuente]
            response = self.session.get(url, timeout=30)
            
            # Buscar link de descarga en la página
            if 'descargar' in response.text.lower():
                # Extraer URL de descarga del HTML
                match = re.search(r'href="([^"]*\.(csv|xlsx?))"', response.text, re.IGNORECASE)
                if match:
                    download_url = match.group(1)
                    if not download_url.startswith('http'):
                        download_url = f"https://snifa.sma.gob.cl{download_url}"
                    
                    # Descargar archivo
                    file_response = self.session.get(download_url, timeout=30)
                    if 'csv' in download_url.lower():
                        df = pd.read_csv(io.StringIO(file_response.text))
                    else:
                        df = pd.read_excel(io.BytesIO(file_response.content))
                    
                    logger.info(f"✅ Fuente alternativa exitosa: {len(df)} registros")
                    return df
        except Exception as e:
            logger.error(f"❌ Fuente alternativa falló: {str(e)}")
        
        return None
    
    def procesar_sanciones_firmes(self, dias_atras: int = 1) -> List[Dict]:
        """
        Procesa sanciones firmes de los últimos días
        """
        df = self.descargar_datos_publicos('sanciones_firmes')
        if df is None or df.empty:
            logger.warning("No se pudieron obtener sanciones firmes")
            return []
        
        sanciones = []
        fecha_limite = datetime.now() - timedelta(days=dias_atras)
        
        # Columnas esperadas (pueden variar según el formato actual)
        columnas_fecha = ['Fecha_Resolucion', 'fecha_resolucion', 'FechaResolucion', 'Fecha']
        columna_fecha = None
        for col in columnas_fecha:
            if col in df.columns:
                columna_fecha = col
                break
        
        if not columna_fecha:
            logger.warning("No se encontró columna de fecha en sanciones")
            return []
        
        for _, row in df.iterrows():
            try:
                # Parsear fecha
                fecha_str = str(row[columna_fecha])
                fecha = pd.to_datetime(fecha_str, errors='coerce')
                
                if pd.isna(fecha) or fecha < fecha_limite:
                    continue
                
                # Extraer información relevante
                empresa = row.get('Empresa', row.get('RazonSocial', row.get('Titular', 'Sin información')))
                expediente = row.get('Expediente', row.get('NumExpediente', row.get('ID', 'S/N')))
                
                # Procesar multa
                multa_valor = 0
                multa_unidad = ''
                multa_texto = ''
                
                if 'Multa' in row or 'MontoMulta' in row or 'Sancion' in row:
                    multa_raw = str(row.get('Multa', row.get('MontoMulta', row.get('Sancion', ''))))
                    
                    # Buscar patrones de multa (ej: "500 UTA", "1000 UTM")
                    match = re.search(r'(\d+(?:\.\d+)?)\s*(UTA|UTM|USD)', multa_raw, re.IGNORECASE)
                    if match:
                        multa_valor = float(match.group(1))
                        multa_unidad = match.group(2).upper()
                        
                        # Convertir a CLP
                        if multa_unidad in self.valores_conversion:
                            valor_clp = multa_valor * self.valores_conversion[multa_unidad]
                            if valor_clp >= 1_000_000_000:
                                multa_texto = f"{multa_valor:.0f} {multa_unidad} (~${valor_clp/1_000_000_000:.1f}MM CLP)"
                            else:
                                multa_texto = f"{multa_valor:.0f} {multa_unidad} (~${valor_clp/1_000_000:.0f}M CLP)"
                        else:
                            multa_texto = f"{multa_valor:.0f} {multa_unidad}"
                
                # Calcular relevancia
                relevancia = self._calcular_relevancia_sancion(multa_valor, multa_unidad)
                
                sancion = {
                    'fuente': 'SMA',
                    'tipo': 'Sanción Firme',
                    'titulo': f"Sanción a {empresa} - {multa_texto or 'Monto no especificado'}",
                    'empresa': empresa,
                    'fecha': fecha.strftime('%d/%m/%Y'),
                    'multa': multa_texto or 'No especificada',
                    'expediente': expediente,
                    'resumen': row.get('Descripcion', row.get('Infracciones', 'Sanción ambiental aplicada')),
                    'relevancia': relevancia,
                    'url': f"https://snifa.sma.gob.cl/Sancionatorio/Ficha/{expediente}"
                }
                
                sanciones.append(sancion)
                
            except Exception as e:
                logger.debug(f"Error procesando fila: {str(e)}")
                continue
        
        logger.info(f"📊 Procesadas {len(sanciones)} sanciones firmes del último día")
        return sanciones
    
    def procesar_procedimientos_sancionatorios(self, dias_atras: int = 1) -> List[Dict]:
        """
        Procesa procedimientos sancionatorios en curso
        """
        df = self.descargar_datos_publicos('procedimientos_sancionatorios')
        if df is None or df.empty:
            logger.warning("No se pudieron obtener procedimientos sancionatorios")
            return []
        
        procedimientos = []
        fecha_limite = datetime.now() - timedelta(days=dias_atras)
        
        # Procesar similar a sanciones firmes
        for _, row in df.iterrows():
            try:
                # Buscar columna de fecha
                fecha_str = None
                for col in ['Fecha_Inicio', 'FechaInicio', 'Fecha', 'fecha_inicio']:
                    if col in df.columns:
                        fecha_str = str(row[col])
                        break
                
                if not fecha_str:
                    continue
                
                fecha = pd.to_datetime(fecha_str, errors='coerce')
                if pd.isna(fecha) or fecha < fecha_limite:
                    continue
                
                empresa = row.get('Empresa', row.get('Titular', 'Sin información'))
                expediente = row.get('Expediente', row.get('ID', 'S/N'))
                
                procedimiento = {
                    'fuente': 'SMA',
                    'tipo': 'Procedimiento Sancionatorio',
                    'titulo': f"Procedimiento iniciado contra {empresa}",
                    'empresa': empresa,
                    'fecha': fecha.strftime('%d/%m/%Y'),
                    'expediente': expediente,
                    'estado': row.get('Estado', 'En curso'),
                    'resumen': row.get('Motivo', row.get('Descripcion', 'Procedimiento sancionatorio en curso')),
                    'relevancia': 6.0,
                    'url': f"https://snifa.sma.gob.cl/Sancionatorio/Ficha/{expediente}"
                }
                
                procedimientos.append(procedimiento)
                
            except Exception as e:
                logger.debug(f"Error procesando procedimiento: {str(e)}")
                continue
        
        logger.info(f"📊 Procesados {len(procedimientos)} procedimientos sancionatorios")
        return procedimientos
    
    def _calcular_relevancia_sancion(self, valor: float, unidad: str) -> float:
        """
        Calcula relevancia basada en el monto de la multa
        """
        if not valor or not unidad:
            return 5.0
        
        # Convertir a CLP para comparación
        valor_clp = valor * self.valores_conversion.get(unidad, 1)
        
        if valor_clp >= 1_000_000_000:  # Más de $1,000M CLP
            return 10.0
        elif valor_clp >= 500_000_000:   # Más de $500M CLP
            return 9.0
        elif valor_clp >= 100_000_000:   # Más de $100M CLP
            return 8.0
        elif valor_clp >= 50_000_000:    # Más de $50M CLP
            return 7.0
        elif valor_clp >= 10_000_000:    # Más de $10M CLP
            return 6.0
        else:
            return 5.0
    
    def obtener_datos_sma(self, dias_atras: int = 1) -> List[Dict]:
        """
        Obtiene todos los datos de SMA (sanciones y procedimientos)
        """
        datos = []
        
        # Obtener sanciones firmes
        sanciones = self.procesar_sanciones_firmes(dias_atras)
        datos.extend(sanciones)
        
        # Obtener procedimientos sancionatorios
        procedimientos = self.procesar_procedimientos_sancionatorios(dias_atras)
        datos.extend(procedimientos)
        
        # Ordenar por relevancia
        datos.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
        
        logger.info(f"✅ Total SMA: {len(datos)} items ({len(sanciones)} sanciones, {len(procedimientos)} procedimientos)")
        
        return datos


def test_snifa_publico():
    """
    Prueba el scraper con datos públicos reales
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🌍 PRUEBA SCRAPER SNIFA - DATOS PÚBLICOS REALES")
    print("="*70)
    
    scraper = ScraperSNIFAPublico()
    
    print("\n📥 Descargando datos públicos de SNIFA...")
    datos = scraper.obtener_datos_sma(dias_atras=30)  # Últimos 30 días para ver más datos
    
    if datos:
        print(f"\n✅ Obtenidos {len(datos)} registros de SMA")
        
        print("\n" + "-"*70)
        print("📋 ÚLTIMAS SANCIONES Y PROCEDIMIENTOS")
        print("-"*70)
        
        for i, item in enumerate(datos[:5], 1):
            print(f"\n{i}. {item['titulo']}")
            print(f"   📅 {item['fecha']} | 🏢 {item['empresa']}")
            if 'multa' in item:
                print(f"   💸 {item.get('multa', 'N/A')}")
            print(f"   📝 {item['resumen'][:100]}...")
            print(f"   ⭐ Relevancia: {item.get('relevancia', 0):.1f}/10")
            print(f"   🔗 {item['url']}")
    else:
        print("\n⚠️ No se obtuvieron datos. Verificando conexión...")
        print("Intentando descargar archivos de prueba...")
        
        # Intentar descargar cada fuente individualmente
        for fuente in scraper.fuentes_datos.keys():
            print(f"\nProbando {fuente}...")
            df = scraper.descargar_datos_publicos(fuente)
            if df is not None:
                print(f"✅ {fuente}: {len(df)} filas")
                print(f"   Columnas: {list(df.columns)[:5]}...")
            else:
                print(f"❌ {fuente}: No se pudo descargar")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    test_snifa_publico()