"""
Scraper para SNIFA usando web scraping directo
Obtiene sanciones y procedimientos sancionatorios del portal SNIFA
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import re
import json

logger = logging.getLogger(__name__)

class ScraperSNIFAWeb:
    def __init__(self):
        """
        Inicializa el scraper con el portal web de SNIFA
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # URL base del portal SNIFA
        self.base_url = "https://snifa.sma.gob.cl"
        
        # Valores de conversión actualizados (Diciembre 2024)
        self.valores_conversion = {
            'UTM': 65770,  # Valor UTM diciembre 2024
            'UTA': 789240,  # Valor UTA 2024 (12 * UTM)
            'USD': 970     # Aproximado
        }
    
    def obtener_sanciones_recientes(self, dias_atras: int = 1) -> List[Dict]:
        """
        Obtiene sanciones firmes recientes desde el registro público
        """
        sanciones = []
        
        try:
            logger.info("📋 Obteniendo sanciones firmes recientes...")
            
            # URL del registro público de sanciones
            url = f"{self.base_url}/RegistroPublico"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tabla de sanciones o lista
            tabla = soup.find('table', {'class': ['tabla-sanciones', 'registro-publico']})
            if not tabla:
                # Buscar divs con información de sanciones
                items = soup.find_all('div', {'class': ['sancion-item', 'registro-item']})
            else:
                items = tabla.find_all('tr')[1:]  # Saltar header
            
            fecha_limite = datetime.now() - timedelta(days=dias_atras)
            
            for item in items:
                try:
                    sancion = self._parsear_sancion(item)
                    if sancion:
                        # Verificar fecha
                        fecha_sancion = datetime.strptime(sancion['fecha'], '%d/%m/%Y')
                        if fecha_sancion >= fecha_limite:
                            sanciones.append(sancion)
                except Exception as e:
                    logger.debug(f"Error parseando sanción: {str(e)}")
                    continue
            
            logger.info(f"✅ Obtenidas {len(sanciones)} sanciones firmes")
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sanciones: {str(e)}")
        
        return sanciones
    
    def obtener_procedimientos_sancionatorios(self, dias_atras: int = 1) -> List[Dict]:
        """
        Obtiene procedimientos sancionatorios en curso
        """
        procedimientos = []
        
        try:
            logger.info("📋 Obteniendo procedimientos sancionatorios...")
            
            # URL de búsqueda de procedimientos
            url = f"{self.base_url}/v2/Sancionatorio"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar lista de procedimientos
            lista = soup.find('div', {'class': 'lista-procedimientos'})
            if not lista:
                # Buscar tabla alternativa
                lista = soup.find('table', {'class': 'tabla-procedimientos'})
            
            if lista:
                items = lista.find_all(['tr', 'div', 'article'])[1:]  # Saltar header si existe
                
                fecha_limite = datetime.now() - timedelta(days=dias_atras)
                
                for item in items:
                    try:
                        procedimiento = self._parsear_procedimiento(item)
                        if procedimiento:
                            # Verificar fecha
                            fecha_proc = datetime.strptime(procedimiento['fecha'], '%d/%m/%Y')
                            if fecha_proc >= fecha_limite:
                                procedimientos.append(procedimiento)
                    except Exception as e:
                        logger.debug(f"Error parseando procedimiento: {str(e)}")
                        continue
            
            logger.info(f"✅ Obtenidos {len(procedimientos)} procedimientos")
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo procedimientos: {str(e)}")
        
        return procedimientos
    
    def buscar_por_expediente(self, expediente: str) -> Optional[Dict]:
        """
        Busca información específica por número de expediente
        """
        try:
            # URL de ficha del expediente
            url = f"{self.base_url}/Sancionatorio/Ficha/{expediente}"
            
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer información de la ficha
            info = {
                'expediente': expediente,
                'fuente': 'SMA',
                'url': url
            }
            
            # Buscar campos específicos
            campos = {
                'Empresa': 'empresa',
                'Titular': 'titular',
                'Fecha': 'fecha',
                'Estado': 'estado',
                'Multa': 'multa',
                'Infracciones': 'infracciones',
                'Resolución': 'resolucion'
            }
            
            for campo_buscar, campo_guardar in campos.items():
                elemento = soup.find(text=re.compile(campo_buscar))
                if elemento:
                    contenedor = elemento.parent.parent if elemento.parent else None
                    if contenedor:
                        valor = contenedor.get_text(strip=True).replace(campo_buscar, '').strip(':').strip()
                        info[campo_guardar] = valor
            
            return info
            
        except Exception as e:
            logger.debug(f"Error buscando expediente {expediente}: {str(e)}")
            return None
    
    def _parsear_sancion(self, elemento) -> Optional[Dict]:
        """
        Parsea un elemento HTML que contiene información de sanción
        """
        try:
            # Extraer texto del elemento
            texto = elemento.get_text(separator=' ', strip=True)
            
            # Buscar patrones comunes
            empresa = 'Sin información'
            fecha = 'Sin fecha'
            multa = 'No especificada'
            expediente = 'S/N'
            
            # Buscar empresa/titular
            match_empresa = re.search(r'(?:Empresa|Titular|Razón Social)[:]\s*([^,\n]+)', texto, re.IGNORECASE)
            if match_empresa:
                empresa = match_empresa.group(1).strip()
            
            # Buscar fecha
            match_fecha = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', texto)
            if match_fecha:
                fecha_raw = match_fecha.group(1)
                # Normalizar formato
                try:
                    fecha_obj = datetime.strptime(fecha_raw.replace('-', '/'), '%d/%m/%Y')
                    fecha = fecha_obj.strftime('%d/%m/%Y')
                except:
                    try:
                        fecha_obj = datetime.strptime(fecha_raw.replace('-', '/'), '%d/%m/%y')
                        fecha = fecha_obj.strftime('%d/%m/%Y')
                    except:
                        pass
            
            # Buscar multa
            match_multa = re.search(r'(\d+(?:\.\d+)?)\s*(UTA|UTM|USD)', texto, re.IGNORECASE)
            if match_multa:
                valor = float(match_multa.group(1))
                unidad = match_multa.group(2).upper()
                
                # Convertir a CLP
                if unidad in self.valores_conversion:
                    valor_clp = valor * self.valores_conversion[unidad]
                    if valor_clp >= 1_000_000_000:
                        multa = f"{valor:.0f} {unidad} (~${valor_clp/1_000_000_000:.1f}MM CLP)"
                    else:
                        multa = f"{valor:.0f} {unidad} (~${valor_clp/1_000_000:.0f}M CLP)"
                else:
                    multa = f"{valor:.0f} {unidad}"
            
            # Buscar expediente
            match_exp = re.search(r'(?:Expediente|Exp\.?|N°)[:]\s*([A-Z]-?\d+(?:-\d+)?)', texto, re.IGNORECASE)
            if match_exp:
                expediente = match_exp.group(1)
            
            # Buscar enlace si es un elemento HTML
            url = ''
            if hasattr(elemento, 'find'):
                enlace = elemento.find('a', href=re.compile(r'/Sancionatorio/'))
                if enlace:
                    url = f"{self.base_url}{enlace.get('href')}"
            
            # Calcular relevancia
            relevancia = self._calcular_relevancia_sancion(multa)
            
            return {
                'fuente': 'SMA',
                'tipo': 'Sanción Firme',
                'titulo': f"Sanción a {empresa} - {multa}",
                'empresa': empresa,
                'fecha': fecha,
                'multa': multa,
                'expediente': expediente,
                'resumen': 'Sanción ambiental aplicada',
                'relevancia': relevancia,
                'url': url or f"{self.base_url}/Sancionatorio/Ficha/{expediente}"
            }
            
        except Exception as e:
            logger.debug(f"Error parseando sanción: {str(e)}")
            return None
    
    def _parsear_procedimiento(self, elemento) -> Optional[Dict]:
        """
        Parsea un elemento HTML que contiene información de procedimiento
        """
        try:
            # Similar a _parsear_sancion pero para procedimientos
            texto = elemento.get_text(separator=' ', strip=True)
            
            empresa = 'Sin información'
            fecha = 'Sin fecha'
            expediente = 'S/N'
            estado = 'En curso'
            
            # Buscar empresa/titular
            match_empresa = re.search(r'(?:Empresa|Titular|Razón Social)[:]\s*([^,\n]+)', texto, re.IGNORECASE)
            if match_empresa:
                empresa = match_empresa.group(1).strip()
            
            # Buscar fecha
            match_fecha = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', texto)
            if match_fecha:
                fecha_raw = match_fecha.group(1)
                try:
                    fecha_obj = datetime.strptime(fecha_raw.replace('-', '/'), '%d/%m/%Y')
                    fecha = fecha_obj.strftime('%d/%m/%Y')
                except:
                    pass
            
            # Buscar expediente
            match_exp = re.search(r'(?:Expediente|Exp\.?|N°)[:]\s*([A-Z]-?\d+(?:-\d+)?)', texto, re.IGNORECASE)
            if match_exp:
                expediente = match_exp.group(1)
            
            # Buscar estado
            match_estado = re.search(r'(?:Estado)[:]\s*([^,\n]+)', texto, re.IGNORECASE)
            if match_estado:
                estado = match_estado.group(1).strip()
            
            # Buscar enlace
            url = ''
            if hasattr(elemento, 'find'):
                enlace = elemento.find('a', href=re.compile(r'/Sancionatorio/'))
                if enlace:
                    url = f"{self.base_url}{enlace.get('href')}"
            
            return {
                'fuente': 'SMA',
                'tipo': 'Procedimiento Sancionatorio',
                'titulo': f"Procedimiento contra {empresa}",
                'empresa': empresa,
                'fecha': fecha,
                'expediente': expediente,
                'estado': estado,
                'resumen': 'Procedimiento sancionatorio en curso',
                'relevancia': 6.0,
                'url': url or f"{self.base_url}/Sancionatorio/Ficha/{expediente}"
            }
            
        except Exception as e:
            logger.debug(f"Error parseando procedimiento: {str(e)}")
            return None
    
    def _calcular_relevancia_sancion(self, multa_texto: str) -> float:
        """
        Calcula relevancia basada en el monto de la multa
        """
        relevancia = 5.0
        
        if 'MM CLP' in multa_texto:
            # Extraer valor en millones
            match = re.search(r'\$?([\d,]+(?:\.\d+)?)\s*MM', multa_texto)
            if match:
                valor = float(match.group(1).replace(',', ''))
                if valor >= 1000:  # Más de $1,000MM CLP
                    relevancia = 10.0
                elif valor >= 500:  # Más de $500MM CLP
                    relevancia = 9.0
                elif valor >= 100:  # Más de $100MM CLP
                    relevancia = 8.0
                elif valor >= 50:   # Más de $50MM CLP
                    relevancia = 7.0
                else:
                    relevancia = 6.0
        elif 'M CLP' in multa_texto:
            # Extraer valor en millones
            match = re.search(r'\$?([\d,]+(?:\.\d+)?)\s*M', multa_texto)
            if match:
                valor = float(match.group(1).replace(',', ''))
                if valor >= 100:  # Más de $100M CLP
                    relevancia = 7.0
                elif valor >= 50:  # Más de $50M CLP
                    relevancia = 6.5
                else:
                    relevancia = 6.0
        
        return relevancia
    
    def obtener_datos_sma(self, dias_atras: int = 1) -> List[Dict]:
        """
        Método principal para obtener todos los datos de SMA
        """
        logger.info(f"🌍 Obteniendo datos de SMA/SNIFA (últimos {dias_atras} días)...")
        
        datos = []
        
        # Obtener sanciones firmes
        sanciones = self.obtener_sanciones_recientes(dias_atras)
        datos.extend(sanciones)
        
        # Obtener procedimientos sancionatorios
        procedimientos = self.obtener_procedimientos_sancionatorios(dias_atras)
        datos.extend(procedimientos)
        
        # Ordenar por relevancia
        datos.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
        
        logger.info(f"✅ Total SMA: {len(datos)} items ({len(sanciones)} sanciones, {len(procedimientos)} procedimientos)")
        
        return datos


def test_snifa_web():
    """
    Prueba el scraper SNIFA con web scraping
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🌍 PRUEBA SCRAPER SNIFA - WEB SCRAPING")
    print("="*70)
    
    scraper = ScraperSNIFAWeb()
    
    # Obtener datos de los últimos 30 días para ver más resultados
    print("\n📋 Obteniendo datos de SMA/SNIFA (últimos 30 días)...")
    datos = scraper.obtener_datos_sma(dias_atras=30)
    
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
            print(f"   📝 {item['resumen']}")
            print(f"   ⭐ Relevancia: {item.get('relevancia', 0):.1f}/10")
            print(f"   🔗 {item['url']}")
    else:
        print("\n⚠️ No se obtuvieron datos")
        print("Intentando buscar expediente específico...")
        
        # Probar con un expediente conocido
        expediente_test = "D-001-2024"
        print(f"\nBuscando expediente {expediente_test}...")
        info = scraper.buscar_por_expediente(expediente_test)
        if info:
            print(f"✅ Información encontrada: {info}")
        else:
            print(f"❌ No se encontró información del expediente")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    test_snifa_web()