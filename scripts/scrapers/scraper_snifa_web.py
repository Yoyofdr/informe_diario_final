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
            
            # URL del registro público de sanciones - Probar año actual y anterior
            año_actual = datetime.now().year
            urls_probar = [
                f"{self.base_url}/RegistroPublico/Resultado/{año_actual}",
                f"{self.base_url}/RegistroPublico/Resultado/{año_actual-1}",
                f"{self.base_url}/RegistroPublico"
            ]
            
            for url in urls_probar:
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Buscar tabla principal
                        tabla = soup.find('table')
                        if tabla:
                            filas = tabla.find_all('tr')
                            logger.info(f"📊 Encontrada tabla con {len(filas)} filas en {url}")
                            
                            # Procesar filas (saltar header)
                            for fila in filas[1:min(len(filas), 100)]:  # Limitar a 100 para pruebas
                                celdas = fila.find_all('td')
                                if len(celdas) >= 8:  # La tabla tiene 9 columnas
                                    try:
                                        # Extraer enlace del expediente
                                        enlace_exp = celdas[1].find('a')
                                        expediente = celdas[1].get_text(strip=True)
                                        url_detalle = f"{self.base_url}{enlace_exp.get('href')}" if enlace_exp else f"{self.base_url}/Sancionatorio/Ficha/{expediente}"
                                        
                                        # Extraer todos los datos disponibles
                                        unidad_fiscalizable = celdas[2].get_text(strip=True)
                                        empresa = celdas[3].get_text(strip=True)
                                        categoria = celdas[4].get_text(strip=True)
                                        region = celdas[5].get_text(strip=True)
                                        multa_texto = celdas[6].get_text(strip=True) if len(celdas) > 6 else "$ 0,00"
                                        estado_pago = celdas[7].get_text(strip=True) if len(celdas) > 7 else "No especificado"
                                        
                                        # Procesar multa
                                        multa_valor = 0
                                        multa_formateada = "Sin multa"
                                        if multa_texto and multa_texto != "$ 0,00":
                                            # Extraer valor numérico
                                            match = re.search(r'[\d,]+\.?\d*', multa_texto.replace('$', ''))
                                            if match:
                                                try:
                                                    multa_valor = float(match.group().replace(',', '.'))
                                                    if multa_valor > 0:
                                                        # Formatear multa
                                                        if multa_valor >= 1000:
                                                            multa_formateada = f"{multa_valor:,.0f} UTA (~${multa_valor * self.valores_conversion['UTA'] / 1_000_000:.0f}M CLP)"
                                                        else:
                                                            multa_formateada = f"{multa_valor:.1f} UTA (~${multa_valor * self.valores_conversion['UTA'] / 1_000_000:.1f}M CLP)"
                                                except:
                                                    multa_formateada = multa_texto
                                        
                                        # Calcular relevancia basada en multa
                                        relevancia = 5.0
                                        if multa_valor > 0:
                                            if multa_valor >= 1000:
                                                relevancia = 10.0
                                            elif multa_valor >= 500:
                                                relevancia = 9.0
                                            elif multa_valor >= 100:
                                                relevancia = 8.0
                                            elif multa_valor >= 50:
                                                relevancia = 7.0
                                            else:
                                                relevancia = 6.0
                                        
                                        # Crear resumen enriquecido
                                        resumen = f"Sanción aplicada a {empresa} ({categoria}) en {region}. "
                                        resumen += f"Unidad fiscalizada: {unidad_fiscalizable}. "
                                        if multa_valor > 0:
                                            resumen += f"Multa de {multa_formateada}."
                                        else:
                                            resumen += "Sanción sin multa económica (posible amonestación o medidas correctivas)."
                                        
                                        # Intentar extraer fecha del expediente (formato D-XXX-YYYY)
                                        fecha_str = 'N/A'
                                        match_fecha = re.search(r'D-\d+-(\d{4})', expediente)
                                        if match_fecha:
                                            año = match_fecha.group(1)
                                            # Usar una fecha estimada del año del expediente
                                            fecha_str = f'01/01/{año}'
                                        
                                        # Si hay una celda adicional que podría ser fecha
                                        if len(celdas) > 8:
                                            fecha_celda = celdas[8].get_text(strip=True)
                                            if re.match(r'\d{2}/\d{2}/\d{4}', fecha_celda):
                                                fecha_str = fecha_celda
                                        
                                        # Parsear datos de las celdas
                                        sancion = {
                                            'fuente': 'SMA',
                                            'tipo': 'Sanción Firme',
                                            'expediente': expediente,
                                            'empresa': empresa,
                                            'unidad_fiscalizable': unidad_fiscalizable,
                                            'categoria': categoria,
                                            'region': region,
                                            'fecha': fecha_str,
                                            'multa': multa_formateada,
                                            'estado_pago': estado_pago,
                                            'resumen': resumen,
                                            'relevancia': relevancia,
                                            'url': url_detalle
                                        }
                                        
                                        # Actualizar título
                                        if multa_valor > 0:
                                            sancion['titulo'] = f"Multa de {multa_formateada} a {empresa}"
                                        else:
                                            sancion['titulo'] = f"Sanción a {empresa} - {categoria}"
                                        
                                        # Solo agregar si cumple con el período
                                        if dias_atras >= 365:  # Si buscamos todo el año
                                            sanciones.append(sancion)
                                        else:
                                            # Verificar fecha si la tenemos
                                            if sancion['fecha'] != 'N/A':
                                                try:
                                                    fecha_sancion = datetime.strptime(sancion['fecha'], '%d/%m/%Y')
                                                    fecha_limite = datetime.now() - timedelta(days=dias_atras)
                                                    if fecha_sancion >= fecha_limite:
                                                        sanciones.append(sancion)
                                                except:
                                                    sanciones.append(sancion)  # Agregar si no podemos parsear fecha
                                            else:
                                                sanciones.append(sancion)  # Agregar si no hay fecha
                                                
                                    except Exception as e:
                                        logger.debug(f"Error parseando fila: {str(e)}")
                                        continue
                            
                            if sanciones:
                                break  # Si encontramos datos, no probar más URLs
                                
                except Exception as e:
                    logger.debug(f"Error con URL {url}: {str(e)}")
                    continue
            
            logger.info(f"✅ Obtenidas {len(sanciones)} sanciones firmes")
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sanciones: {str(e)}")
        
        return sanciones[:10]  # Limitar a 10 para el informe
    
    def obtener_procedimientos_sancionatorios(self, dias_atras: int = 1) -> List[Dict]:
        """
        Obtiene procedimientos sancionatorios en curso
        """
        procedimientos = []
        
        try:
            logger.info("📋 Obteniendo procedimientos sancionatorios...")
            
            # URLs de procedimientos - Probar diferentes endpoints
            año_actual = datetime.now().year
            urls_probar = [
                f"{self.base_url}/Sancionatorio/Resultado/{año_actual}",
                f"{self.base_url}/Sancionatorio/Resultado/{año_actual-1}",
                f"{self.base_url}/v2/Sancionatorio"
            ]
            
            for url in urls_probar:
                try:
                    response = self.session.get(url, timeout=30, allow_redirects=True)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Buscar tabla principal
                        tabla = soup.find('table')
                        if tabla:
                            filas = tabla.find_all('tr')
                            logger.info(f"📊 Encontrada tabla con {len(filas)} filas en {url}")
                            
                            # Procesar filas (saltar header)
                            for fila in filas[1:min(len(filas), 50)]:  # Limitar a 50 para pruebas
                                celdas = fila.find_all('td')
                                if len(celdas) >= 7:  # La tabla tiene 8 columnas
                                    try:
                                        # Extraer enlace del expediente
                                        enlace_exp = celdas[1].find('a')
                                        expediente = celdas[1].get_text(strip=True)
                                        url_detalle = f"{self.base_url}{enlace_exp.get('href')}" if enlace_exp else f"{self.base_url}/Sancionatorio/Ficha/{expediente}"
                                        
                                        # Extraer todos los datos disponibles
                                        unidad_fiscalizable = celdas[2].get_text(strip=True)
                                        empresas_texto = celdas[3].get_text(strip=True)
                                        # Puede haber múltiples empresas, tomar la primera
                                        empresa = empresas_texto.split('SPA')[0] + 'SPA' if 'SPA' in empresas_texto else empresas_texto.split('S.A')[0] + 'S.A' if 'S.A' in empresas_texto else empresas_texto[:50]
                                        categoria = celdas[4].get_text(strip=True)
                                        region = celdas[5].get_text(strip=True)
                                        estado = celdas[6].get_text(strip=True) if len(celdas) > 6 else "En curso"
                                        
                                        # Calcular relevancia basada en categoría y estado
                                        relevancia = 6.0
                                        if estado.lower() == "en curso":
                                            relevancia += 1.0
                                        
                                        # Categorías más relevantes
                                        categorias_relevantes = ['Minería', 'Energía', 'Pesca y Acuicultura', 'Instalación fabril']
                                        if any(cat in categoria for cat in categorias_relevantes):
                                            relevancia += 2.0
                                        
                                        # Crear resumen enriquecido
                                        resumen = f"Procedimiento sancionatorio iniciado contra {empresa} "
                                        resumen += f"por actividades en {unidad_fiscalizable} ({categoria}). "
                                        resumen += f"Ubicación: {region}. Estado actual: {estado}. "
                                        resumen += f"El procedimiento está en evaluación por posibles infracciones ambientales."
                                        
                                        # Intentar extraer fecha del expediente (formato D-XXX-YYYY)
                                        fecha_str = 'N/A'
                                        match_fecha = re.search(r'D-\d+-(\d{4})', expediente)
                                        if match_fecha:
                                            año = match_fecha.group(1)
                                            # Usar una fecha estimada del año del expediente
                                            fecha_str = f'01/01/{año}'
                                        
                                        # Si hay una celda adicional que podría ser fecha
                                        if len(celdas) > 7:
                                            fecha_celda = celdas[7].get_text(strip=True)
                                            if re.match(r'\d{2}/\d{2}/\d{4}', fecha_celda):
                                                fecha_str = fecha_celda
                                        
                                        # Parsear datos de las celdas
                                        procedimiento = {
                                            'fuente': 'SMA',
                                            'tipo': 'Procedimiento Sancionatorio',
                                            'expediente': expediente,
                                            'empresa': empresa,
                                            'unidad_fiscalizable': unidad_fiscalizable,
                                            'categoria': categoria,
                                            'region': region,
                                            'fecha': fecha_str,
                                            'estado': estado,
                                            'resumen': resumen,
                                            'relevancia': min(relevancia, 10.0),
                                            'url': url_detalle
                                        }
                                        
                                        # Actualizar título según estado
                                        if estado.lower() == "en curso":
                                            procedimiento['titulo'] = f"Procedimiento en curso contra {empresa} - {categoria}"
                                        else:
                                            procedimiento['titulo'] = f"Procedimiento {estado} - {empresa}"
                                        
                                        # Filtrar por expedientes D- (procedimientos)
                                        if procedimiento['expediente'].startswith('D-'):
                                            # Solo agregar si cumple con el período
                                            if dias_atras >= 365:
                                                procedimientos.append(procedimiento)
                                            elif procedimiento['fecha'] != 'N/A':
                                                try:
                                                    fecha_proc = datetime.strptime(procedimiento['fecha'], '%d/%m/%Y')
                                                    fecha_limite = datetime.now() - timedelta(days=dias_atras)
                                                    if fecha_proc >= fecha_limite:
                                                        procedimientos.append(procedimiento)
                                                except:
                                                    procedimientos.append(procedimiento)
                                            else:
                                                procedimientos.append(procedimiento)
                                                
                                    except Exception as e:
                                        logger.debug(f"Error parseando fila: {str(e)}")
                                        continue
                            
                            if procedimientos:
                                break  # Si encontramos datos, no probar más URLs
                                
                except Exception as e:
                    logger.debug(f"Error con URL {url}: {str(e)}")
                    continue
            
            logger.info(f"✅ Obtenidos {len(procedimientos)} procedimientos")
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo procedimientos: {str(e)}")
        
        return procedimientos[:10]  # Limitar a 10 para el informe
    
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
        
        # Si no hay datos o todos sin fecha, retornar lista vacía
        datos_con_fecha = [d for d in datos if d.get('fecha') != 'N/A']
        if not datos_con_fecha:
            logger.warning("No se encontraron sanciones con fechas válidas")
            datos = []
        
        # Ordenar por relevancia
        datos.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
        
        logger.info(f"✅ Total SMA: {len(datos)} items")
        
        return datos
    
    # Método eliminado - no usar datos de ejemplo


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