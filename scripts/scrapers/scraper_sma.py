"""
Scraper para la Superintendencia del Medio Ambiente (SMA)
Obtiene sanciones, multas y resoluciones sancionatorias recientes
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import json
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class ScraperSMA:
    def __init__(self):
        self.base_url = "https://snifa.sma.gob.cl"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Referer': 'https://snifa.sma.gob.cl'
        })
    
    def obtener_sanciones_recientes(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene sanciones aplicadas por la SMA en los últimos días
        
        Args:
            dias_atras: Número de días hacia atrás para buscar
            
        Returns:
            Lista de sanciones con sus detalles
        """
        sanciones = []
        
        # Intentar múltiples endpoints
        sanciones.extend(self._obtener_registro_publico_sanciones())
        sanciones.extend(self._obtener_expedientes_sancionatorios())
        sanciones.extend(self._obtener_resoluciones_recientes())
        
        # Filtrar por fecha si es posible
        fecha_limite = datetime.now() - timedelta(days=dias_atras)
        sanciones_filtradas = self._filtrar_por_fecha(sanciones, fecha_limite)
        
        return self._eliminar_duplicados(sanciones_filtradas)
    
    def _obtener_registro_publico_sanciones(self) -> List[Dict]:
        """
        Obtiene sanciones del registro público
        """
        try:
            # Intentar varias URLs posibles
            urls = [
                f"{self.base_url}/RegistroPublico",
                f"{self.base_url}/RegistroPublico/Sanciones",
                f"{self.base_url}/Sancionatorio/Sanciones",
                "https://portal.sma.gob.cl/index.php/registro-publico-de-sanciones/"
            ]
            
            for url in urls:
                try:
                    logger.info(f"🔍 Intentando URL: {url}")
                    response = self.session.get(url, timeout=30, allow_redirects=True)
                    if response.status_code == 200:
                        break
                except:
                    continue
            else:
                logger.warning("No se pudo acceder al registro público")
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            sanciones = []
            
            # Buscar tabla de sanciones
            tablas = soup.find_all('table', class_=['table', 'tabla_datos', 'table-striped'])
            
            for tabla in tablas:
                filas = tabla.find_all('tr')[1:]  # Saltar encabezado
                
                for fila in filas:
                    sancion = self._extraer_sancion_de_fila(fila)
                    if sancion:
                        sanciones.append(sancion)
            
            # Si no hay tablas, buscar divs o listas
            if not sanciones:
                sanciones.extend(self._buscar_sanciones_en_divs(soup))
            
            logger.info(f"✅ Encontradas {len(sanciones)} sanciones en registro público")
            return sanciones
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo registro público SMA: {str(e)}")
            return []
    
    def _obtener_expedientes_sancionatorios(self) -> List[Dict]:
        """
        Obtiene expedientes sancionatorios recientes
        """
        try:
            url = f"{self.base_url}/Sancionatorio"
            logger.info(f"🔍 Consultando expedientes sancionatorios")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            expedientes = []
            
            # Buscar listados de expedientes
            elementos = soup.find_all(['div', 'article', 'section'], 
                                     class_=re.compile('expediente|sancion|procedimiento', re.I))
            
            for elemento in elementos:
                expediente = self._extraer_expediente(elemento)
                if expediente:
                    expedientes.append(expediente)
            
            logger.info(f"✅ Encontrados {len(expedientes)} expedientes sancionatorios")
            return expedientes
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo expedientes SMA: {str(e)}")
            return []
    
    def _obtener_resoluciones_recientes(self) -> List[Dict]:
        """
        Obtiene resoluciones sancionatorias recientes
        """
        try:
            # Intentar buscar en la sección de resoluciones
            url = f"{self.base_url}/Resolucion/Sancionatorias"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 404:
                # Intentar URL alternativa
                url = f"{self.base_url}/Resoluciones"
                response = self.session.get(url, timeout=30)
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            resoluciones = []
            
            # Buscar enlaces a resoluciones
            for link in soup.find_all('a', href=True):
                texto = link.text.strip()
                href = link['href']
                
                if any(palabra in texto.lower() for palabra in ['resolución', 'multa', 'sanción']):
                    resolucion = {
                        'tipo': 'Resolución Sancionatoria',
                        'titulo': texto,
                        'url': urljoin(self.base_url, href),
                        'fecha': self._extraer_fecha_de_texto(texto),
                        'fuente': 'SMA'
                    }
                    
                    # Intentar extraer más detalles
                    resolucion.update(self._extraer_detalles_resolucion(link.parent))
                    resoluciones.append(resolucion)
            
            return resoluciones
            
        except Exception as e:
            logger.error(f"Error obteniendo resoluciones: {str(e)}")
            return []
    
    def _extraer_sancion_de_fila(self, fila) -> Optional[Dict]:
        """
        Extrae datos de sanción desde una fila de tabla
        """
        try:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 2:
                return None
            
            sancion = {
                'tipo': 'Sanción',
                'fuente': 'SMA'
            }
            
            # Intentar extraer información de las celdas
            for i, celda in enumerate(celdas):
                texto = celda.text.strip()
                
                # Identificar tipo de información por posición o contenido
                if i == 0 or 'expediente' in texto.lower():
                    sancion['expediente'] = texto
                elif 'rut' in texto.lower() or self._es_rut(texto):
                    sancion['rut_empresa'] = texto
                elif any(empresa in texto.upper() for empresa in ['S.A.', 'LTDA', 'SPA', 'EIRL']):
                    sancion['empresa'] = texto
                elif '$' in texto or 'uta' in texto.lower() or 'utm' in texto.lower():
                    sancion['multa'] = self._extraer_monto(texto)
                    sancion['multa_texto'] = texto
                elif self._es_fecha(texto):
                    sancion['fecha'] = texto
                elif 'resolución' in texto.lower():
                    sancion['resolucion'] = texto
                
                # Buscar enlaces
                link = celda.find('a')
                if link and link.get('href'):
                    sancion['url'] = urljoin(self.base_url, link['href'])
            
            # Validar que tenga información mínima
            if sancion.get('empresa') or sancion.get('expediente'):
                return sancion
                
        except Exception as e:
            logger.error(f"Error extrayendo sanción de fila: {str(e)}")
        
        return None
    
    def _buscar_sanciones_en_divs(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Busca sanciones en elementos div cuando no hay tablas
        """
        sanciones = []
        
        # Buscar divs con información de sanciones
        divs = soup.find_all('div', class_=re.compile('sancion|multa|expediente', re.I))
        
        for div in divs:
            texto = div.text.strip()
            
            if len(texto) > 50:  # Filtrar divs muy cortos
                sancion = {
                    'tipo': 'Sanción',
                    'fuente': 'SMA',
                    'texto_completo': texto[:500]
                }
                
                # Extraer información del texto
                sancion['empresa'] = self._extraer_empresa(texto)
                sancion['multa'] = self._extraer_monto(texto)
                sancion['fecha'] = self._extraer_fecha_de_texto(texto)
                
                # Buscar enlaces
                link = div.find('a')
                if link and link.get('href'):
                    sancion['url'] = urljoin(self.base_url, link['href'])
                    sancion['titulo'] = link.text.strip()
                
                if sancion.get('empresa') or sancion.get('multa'):
                    sanciones.append(sancion)
        
        return sanciones
    
    def _extraer_expediente(self, elemento) -> Optional[Dict]:
        """
        Extrae información de un expediente sancionatorio
        """
        try:
            expediente = {
                'tipo': 'Expediente Sancionatorio',
                'fuente': 'SMA'
            }
            
            # Extraer texto
            texto = elemento.text.strip()
            
            # Buscar número de expediente
            match = re.search(r'[A-Z]+-\d+-\d{4}', texto)
            if match:
                expediente['numero'] = match.group()
            
            # Extraer empresa
            expediente['empresa'] = self._extraer_empresa(texto)
            
            # Extraer fecha
            expediente['fecha'] = self._extraer_fecha_de_texto(texto)
            
            # Buscar enlaces
            link = elemento.find('a')
            if link and link.get('href'):
                expediente['url'] = urljoin(self.base_url, link['href'])
                expediente['titulo'] = link.text.strip()
            
            # Extraer estado
            for estado in ['En tramitación', 'Finalizado', 'Sanción aplicada', 'Archivado']:
                if estado.lower() in texto.lower():
                    expediente['estado'] = estado
                    break
            
            if expediente.get('numero') or expediente.get('empresa'):
                return expediente
                
        except Exception as e:
            logger.error(f"Error extrayendo expediente: {str(e)}")
        
        return None
    
    def _extraer_detalles_resolucion(self, elemento) -> Dict:
        """
        Extrae detalles adicionales de una resolución
        """
        detalles = {}
        
        try:
            texto = elemento.text if elemento else ""
            
            # Extraer número de resolución
            match = re.search(r'Res[.\s]*(?:Ex[.\s]*)?\s*N?°?\s*(\d+)', texto, re.I)
            if match:
                detalles['numero_resolucion'] = match.group(1)
            
            # Extraer empresa
            detalles['empresa'] = self._extraer_empresa(texto)
            
            # Extraer monto de multa
            detalles['multa'] = self._extraer_monto(texto)
            
            # Extraer tipo de infracción
            infracciones = ['emisiones', 'vertimiento', 'residuos', 'ruido', 'olores']
            for infraccion in infracciones:
                if infraccion in texto.lower():
                    detalles['infraccion'] = infraccion
                    break
                    
        except Exception as e:
            logger.error(f"Error extrayendo detalles de resolución: {str(e)}")
        
        return detalles
    
    def _extraer_empresa(self, texto: str) -> Optional[str]:
        """
        Extrae el nombre de la empresa del texto
        """
        # Buscar patrones comunes de empresas
        patrones = [
            r'([A-Z][A-Za-zÁÉÍÓÚáéíóúñÑ\s&]+(?:S\.A\.|LTDA|SPA|EIRL|SpA))',
            r'Titular:\s*([^\n]+)',
            r'Empresa:\s*([^\n]+)',
            r'Razón Social:\s*([^\n]+)'
        ]
        
        for patron in patrones:
            match = re.search(patron, texto)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extraer_monto(self, texto: str) -> Optional[Dict]:
        """
        Extrae el monto de multa del texto
        """
        monto = {}
        
        # Buscar UTA
        match = re.search(r'([\d.,]+)\s*UTA', texto, re.I)
        if match:
            try:
                valor = float(match.group(1).replace(',', '.'))
                monto['valor'] = valor
                monto['unidad'] = 'UTA'
                monto['valor_clp'] = valor * 60000 * 12  # Aproximado
                return monto
            except:
                pass
        
        # Buscar UTM
        match = re.search(r'([\d.,]+)\s*UTM', texto, re.I)
        if match:
            try:
                valor = float(match.group(1).replace(',', '.'))
                monto['valor'] = valor
                monto['unidad'] = 'UTM'
                monto['valor_clp'] = valor * 65000  # Aproximado
                return monto
            except:
                pass
        
        # Buscar pesos chilenos
        match = re.search(r'\$\s*([\d.,]+)', texto)
        if match:
            try:
                valor_texto = match.group(1).replace('.', '').replace(',', '.')
                valor = float(valor_texto)
                monto['valor'] = valor
                monto['unidad'] = 'CLP'
                monto['valor_clp'] = valor
                return monto
            except:
                pass
        
        return None
    
    def _extraer_fecha_de_texto(self, texto: str) -> Optional[str]:
        """
        Extrae fecha del texto
        """
        # Patrones de fecha comunes
        patrones = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY o DD-MM-YYYY
            r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',  # DD de mes de YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})'  # YYYY-MM-DD
        ]
        
        for patron in patrones:
            match = re.search(patron, texto)
            if match:
                return match.group()
        
        return None
    
    def _es_fecha(self, texto: str) -> bool:
        """
        Verifica si un texto parece ser una fecha
        """
        return bool(self._extraer_fecha_de_texto(texto))
    
    def _es_rut(self, texto: str) -> bool:
        """
        Verifica si un texto parece ser un RUT
        """
        patron = r'\d{1,2}\.\d{3}\.\d{3}-[\dkK]'
        return bool(re.match(patron, texto.strip()))
    
    def _filtrar_por_fecha(self, sanciones: List[Dict], fecha_limite: datetime) -> List[Dict]:
        """
        Filtra sanciones por fecha
        """
        filtradas = []
        
        for sancion in sanciones:
            fecha_str = sancion.get('fecha')
            
            if not fecha_str:
                # Si no tiene fecha, incluirla por si acaso (puede ser reciente)
                filtradas.append(sancion)
                continue
            
            try:
                # Intentar parsear la fecha
                fecha = self._parsear_fecha(fecha_str)
                if fecha and fecha >= fecha_limite:
                    filtradas.append(sancion)
            except:
                # Si no se puede parsear, incluirla por si acaso
                filtradas.append(sancion)
        
        return filtradas
    
    def _parsear_fecha(self, fecha_str: str) -> Optional[datetime]:
        """
        Intenta parsear una fecha en varios formatos
        """
        formatos = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%d de %B de %Y'
        ]
        
        # Mapeo de meses en español
        meses = {
            'enero': 'January', 'febrero': 'February', 'marzo': 'March',
            'abril': 'April', 'mayo': 'May', 'junio': 'June',
            'julio': 'July', 'agosto': 'August', 'septiembre': 'September',
            'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
        }
        
        # Reemplazar meses en español
        fecha_str_en = fecha_str
        for mes_es, mes_en in meses.items():
            fecha_str_en = fecha_str_en.replace(mes_es, mes_en)
        
        for formato in formatos:
            try:
                return datetime.strptime(fecha_str_en, formato)
            except:
                continue
        
        return None
    
    def _eliminar_duplicados(self, sanciones: List[Dict]) -> List[Dict]:
        """
        Elimina sanciones duplicadas
        """
        vistos = set()
        unicos = []
        
        for sancion in sanciones:
            # Crear identificador único
            id_unico = (
                sancion.get('expediente', '') + 
                sancion.get('empresa', '') + 
                sancion.get('numero_resolucion', '')
            )
            
            if id_unico and id_unico not in vistos:
                vistos.add(id_unico)
                unicos.append(sancion)
            elif not id_unico:
                # Si no tiene identificador, incluirla de todos modos
                unicos.append(sancion)
        
        return unicos
    
    def obtener_detalles_sancion(self, sancion: Dict) -> Dict:
        """
        Obtiene detalles adicionales de una sanción específica
        """
        try:
            if not sancion.get('url'):
                return sancion
            
            response = self.session.get(sancion['url'], timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer información adicional
            sancion['descripcion'] = self._extraer_descripcion_sancion(soup)
            sancion['infracciones'] = self._extraer_infracciones(soup)
            sancion['medidas'] = self._extraer_medidas(soup)
            
            return sancion
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles de sanción: {str(e)}")
            return sancion
    
    def _extraer_descripcion_sancion(self, soup: BeautifulSoup) -> str:
        """
        Extrae la descripción de la sanción
        """
        # Buscar en diferentes posibles ubicaciones
        for selector in ['.descripcion', '.resumen', '.antecedentes']:
            elemento = soup.select_one(selector)
            if elemento:
                return elemento.text.strip()[:500]
        
        # Buscar en párrafos
        for p in soup.find_all('p'):
            texto = p.text.strip()
            if len(texto) > 100 and any(palabra in texto.lower() 
                                       for palabra in ['infracción', 'incumplimiento', 'sanción']):
                return texto[:500]
        
        return ""
    
    def _extraer_infracciones(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae las infracciones cometidas
        """
        infracciones = []
        
        # Buscar lista de infracciones
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li'):
                texto = li.text.strip()
                if any(palabra in texto.lower() 
                      for palabra in ['infracción', 'incumplimiento', 'violación']):
                    infracciones.append(texto[:200])
        
        return infracciones[:5]  # Limitar cantidad
    
    def _extraer_medidas(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae las medidas o sanciones aplicadas
        """
        medidas = []
        
        # Buscar medidas
        for elemento in soup.find_all(['p', 'li', 'div']):
            texto = elemento.text.strip()
            if any(palabra in texto.lower() 
                  for palabra in ['multa', 'clausura', 'amonestación', 'revocación']):
                medidas.append(texto[:200])
        
        return medidas[:3]  # Limitar cantidad
    
    def formatear_para_informe(self, sanciones: List[Dict]) -> List[Dict]:
        """
        Formatea las sanciones para incluir en el informe diario
        """
        formateadas = []
        
        for sancion in sanciones:
            # Filtrar sanciones poco relevantes
            if not sancion.get('empresa') and not sancion.get('expediente'):
                continue
            
            formateada = {
                'fuente': 'SMA',
                'tipo': sancion.get('tipo', 'Sanción Ambiental'),
                'titulo': self._generar_titulo_sancion(sancion),
                'empresa': sancion.get('empresa', 'No especificada'),
                'fecha': sancion.get('fecha', ''),
                'multa': self._formatear_multa(sancion.get('multa')),
                'url': sancion.get('url', ''),
                'resumen': self._generar_resumen_sancion(sancion),
                'relevancia': self._calcular_relevancia_sancion(sancion)
            }
            
            if sancion.get('expediente'):
                formateada['expediente'] = sancion['expediente']
            
            formateadas.append(formateada)
        
        # Ordenar por relevancia
        formateadas.sort(key=lambda x: x['relevancia'], reverse=True)
        
        return formateadas[:10]  # Limitar a 10 más relevantes
    
    def _generar_titulo_sancion(self, sancion: Dict) -> str:
        """
        Genera un título descriptivo para la sanción
        """
        partes = []
        
        if sancion.get('empresa'):
            partes.append(f"Sanción a {sancion['empresa']}")
        elif sancion.get('expediente'):
            partes.append(f"Expediente {sancion['expediente']}")
        else:
            partes.append("Sanción Ambiental")
        
        if sancion.get('multa'):
            multa_texto = self._formatear_multa(sancion['multa'])
            if multa_texto:
                partes.append(f"- Multa {multa_texto}")
        
        return " ".join(partes)
    
    def _formatear_multa(self, multa: Optional[Dict]) -> str:
        """
        Formatea el monto de la multa
        """
        if not multa:
            return ""
        
        if multa.get('unidad') == 'UTA':
            return f"{multa['valor']:.0f} UTA"
        elif multa.get('unidad') == 'UTM':
            return f"{multa['valor']:.0f} UTM"
        elif multa.get('valor_clp'):
            millones = multa['valor_clp'] / 1000000
            if millones >= 1:
                return f"${millones:.1f}M CLP"
            else:
                miles = multa['valor_clp'] / 1000
                return f"${miles:.0f}K CLP"
        
        return ""
    
    def _generar_resumen_sancion(self, sancion: Dict) -> str:
        """
        Genera un resumen de la sanción
        """
        partes = []
        
        # Tipo de sanción
        if sancion.get('tipo'):
            partes.append(sancion['tipo'])
        
        # Descripción o infracciones
        if sancion.get('descripcion'):
            partes.append(sancion['descripcion'][:150])
        elif sancion.get('infracciones'):
            partes.append(f"Infracciones: {', '.join(sancion['infracciones'][:2])}")
        elif sancion.get('texto_completo'):
            partes.append(sancion['texto_completo'][:150])
        
        # Estado si existe
        if sancion.get('estado'):
            partes.append(f"Estado: {sancion['estado']}")
        
        return ". ".join(partes)
    
    def _calcular_relevancia_sancion(self, sancion: Dict) -> float:
        """
        Calcula la relevancia de una sanción
        """
        score = 0.0
        
        # Multa (más importante)
        if sancion.get('multa'):
            valor_clp = sancion['multa'].get('valor_clp', 0)
            if valor_clp > 100000000:  # Más de 100M CLP
                score += 10
            elif valor_clp > 50000000:  # Más de 50M CLP
                score += 7
            elif valor_clp > 10000000:  # Más de 10M CLP
                score += 5
            elif valor_clp > 1000000:  # Más de 1M CLP
                score += 3
            else:
                score += 1
        
        # Empresa conocida
        if sancion.get('empresa'):
            empresa = sancion['empresa'].upper()
            # Empresas grandes o conocidas
            empresas_relevantes = ['CODELCO', 'ENAP', 'COPEC', 'ARAUCO', 'SQM', 'CAP', 'ENGIE']
            for emp in empresas_relevantes:
                if emp in empresa:
                    score += 3
                    break
        
        # Tipo de infracción (más grave)
        if sancion.get('infracciones'):
            infracciones_graves = ['contaminación', 'vertimiento', 'emisiones', 'daño ambiental']
            for infraccion in sancion['infracciones']:
                for grave in infracciones_graves:
                    if grave in infraccion.lower():
                        score += 2
                        break
        
        # Reciente (fecha)
        if sancion.get('fecha'):
            try:
                fecha = self._parsear_fecha(sancion['fecha'])
                if fecha:
                    dias = (datetime.now() - fecha).days
                    if dias <= 1:
                        score += 3
                    elif dias <= 7:
                        score += 2
                    elif dias <= 30:
                        score += 1
            except:
                pass
        
        return score


def test_scraper_sma():
    """
    Función de prueba del scraper SMA
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = ScraperSMA()
    
    print("\n=== PRUEBA SCRAPER SMA ===\n")
    print("Buscando sanciones de los últimos 30 días...")
    
    sanciones = scraper.obtener_sanciones_recientes(dias_atras=30)
    
    if sanciones:
        print(f"\n✅ Encontradas {len(sanciones)} sanciones\n")
        
        # Mostrar primera sanción en detalle
        if sanciones:
            print("--- EJEMPLO DE SANCIÓN ---")
            print(json.dumps(sanciones[0], indent=2, ensure_ascii=False, default=str))
        
        # Formatear para informe
        print("\n--- SANCIONES FORMATEADAS PARA INFORME ---")
        formateadas = scraper.formatear_para_informe(sanciones)
        
        for i, sancion in enumerate(formateadas[:5], 1):
            print(f"\n{i}. {sancion['titulo']}")
            if sancion.get('multa'):
                print(f"   Multa: {sancion['multa']}")
            print(f"   {sancion['resumen']}")
            print(f"   Relevancia: {sancion['relevancia']:.1f}")
    else:
        print("❌ No se encontraron sanciones")


if __name__ == "__main__":
    test_scraper_sma()