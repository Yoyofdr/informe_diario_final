#!/usr/bin/env python3
"""
Scraper integrado para proyectos de ley del día anterior
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import re
import os
import sys
from pathlib import Path
import openai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio base al path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Importar servicios de extracción de PDF
try:
    from alerts.services.pdf_extractor import pdf_extractor
except ImportError:
    pdf_extractor = None

# Configurar OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperProyectosLeyIntegrado:
    def __init__(self):
        self.base_url = "https://www.camara.cl"
        self.search_url = f"{self.base_url}/legislacion/proyectosdeley/proyectos_ley.aspx"
        self.senado_base = "https://www.senado.cl"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def _fechas_equivalentes(self, fecha1: str, fecha2: str) -> bool:
        """
        Compara dos fechas en formato DD/MM/YYYY permitiendo variaciones
        como falta de ceros (2/9/2025 vs 02/09/2025)
        """
        try:
            # Normalizar ambas fechas a datetime y comparar
            from datetime import datetime
            
            # Intentar parsear fecha1
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                try:
                    dt1 = datetime.strptime(fecha1, fmt)
                    break
                except:
                    continue
            else:
                return False
            
            # Intentar parsear fecha2
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                try:
                    dt2 = datetime.strptime(fecha2, fmt)
                    break
                except:
                    continue
            else:
                return False
            
            return dt1 == dt2
        except:
            return False
    
    def obtener_proyectos_dia_anterior(self, fecha_informe: str = None) -> List[Dict]:
        """
        Obtiene los proyectos ingresados el día anterior
        NOTA: Para el informe del día N, incluye proyectos del día N-1
        
        Args:
            fecha_informe: Fecha del informe en formato DD-MM-YYYY. Si es None, usa fecha actual
        """
        # Si se proporciona fecha del informe, usar el día anterior a esa fecha
        if fecha_informe:
            try:
                # Convertir DD-MM-YYYY a datetime
                fecha_informe_dt = datetime.strptime(fecha_informe, "%d-%m-%Y")
                ayer = fecha_informe_dt - timedelta(days=1)
            except:
                # Si hay error en el formato, usar fecha actual
                ayer = datetime.now() - timedelta(days=1)
        else:
            # Calcular fecha del día anterior a hoy
            ayer = datetime.now() - timedelta(days=1)
        
        fecha_busqueda = ayer.strftime('%d/%m/%Y')
        
        logger.info(f"Buscando proyectos del {fecha_busqueda}")
        
        proyectos = []
        
        # Buscar en Congreso Nacional (últimos 7 días para luego filtrar)
        proyectos_recientes = self._buscar_proyectos_camara_recientes(dias_atras=7)
        
        # Filtrar solo los que realmente son del día anterior
        proyectos_filtrados = []
        proyectos_vistos = set()  # Para evitar duplicados por número de boletín
        
        for proyecto in proyectos_recientes:
            # Primero obtener detalles para tener la fecha real
            try:
                proyecto_con_detalle = self.obtener_detalle_proyecto(proyecto)
            except Exception as e:
                logger.error(f"Error obteniendo detalles del proyecto {proyecto.get('boletin', 'desconocido')}: {e}")
                continue
            
            # Verificar si la fecha de ingreso coincide con ayer
            fecha_ingreso = proyecto_con_detalle.get('fecha_ingreso', '')
            boletin = proyecto_con_detalle.get('boletin', '')
            
            # LOG CRÍTICO: Mostrar TODAS las fechas que se están comparando
            logger.info(f"Comparando fechas - Buscada: '{fecha_busqueda}' vs Encontrada: '{fecha_ingreso}' para boletín {boletin}")
            
            # Evitar duplicados por número de boletín
            if boletin and boletin in proyectos_vistos:
                logger.debug(f"Proyecto {boletin} ya procesado, omitiendo duplicado")
                continue
            
            # Mejorar comparación de fechas - normalizar formatos
            fecha_match = False
            
            if fecha_ingreso:
                # Comparación exacta
                if fecha_ingreso == fecha_busqueda:
                    fecha_match = True
                # Comparación flexible (sin ceros)
                elif self._fechas_equivalentes(fecha_ingreso, fecha_busqueda):
                    fecha_match = True
                    logger.warning(f"Fechas equivalentes pero formato diferente: '{fecha_ingreso}' vs '{fecha_busqueda}'")
                
            if fecha_match:
                proyectos_filtrados.append(proyecto_con_detalle)
                if boletin:
                    proyectos_vistos.add(boletin)
                logger.info(f"✅ Proyecto {boletin} incluido - fecha {fecha_ingreso}")
            else:
                logger.warning(f"❌ Proyecto {boletin} excluido - fecha no coincide: '{fecha_ingreso}' != '{fecha_busqueda}'")
        
        logger.info(f"Total proyectos únicos ingresados el {fecha_busqueda}: {len(proyectos_filtrados)}")
        
        return proyectos_filtrados
    
    def _buscar_proyectos_camara_recientes(self, dias_atras: int = 7) -> List[Dict]:
        """
        Busca proyectos recientes de los últimos días
        """
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=dias_atras)
        
        try:
            response = self.session.get(self.search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer valores del formulario
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            viewstate_value = viewstate['value'] if viewstate else ''
            
            viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
            viewstate_generator_value = viewstate_generator['value'] if viewstate_generator else ''
            
            event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})
            event_validation_value = event_validation['value'] if event_validation else ''
            
            # Buscar proyectos de los últimos días
            form_data = {
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate_value,
                '__VIEWSTATEGENERATOR': viewstate_generator_value,
                '__EVENTVALIDATION': event_validation_value,
                'ctl00$mainPlaceHolder$txtFechaDesde': fecha_desde.strftime('%d/%m/%Y'),
                'ctl00$mainPlaceHolder$txtFechaHasta': fecha_hasta.strftime('%d/%m/%Y'),
                'ctl00$mainPlaceHolder$btnBuscar': 'Buscar'
            }
            
            response = self.session.post(self.search_url, data=form_data)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            proyectos = []
            
            # Buscar tabla de resultados
            tabla = soup.find('table', {'id': 'mainPlaceHolder_grvResultado'})
            
            if tabla:
                filas = tabla.find_all('tr')[1:]  # Saltar header
                for fila in filas:
                    celdas = fila.find_all('td')
                    if len(celdas) >= 3:
                        proyecto = {}
                        
                        # Boletín y URL
                        if celdas[0].find('a'):
                            link = celdas[0].find('a')
                            texto = link.get_text(strip=True)
                            match = re.search(r'(\d{4,5}-\d{2})', texto)
                            if match:
                                proyecto['boletin'] = match.group(1)
                                proyecto['url_detalle'] = self.base_url + link.get('href', '')
                        
                        # Título
                        if len(celdas) > 2:
                            proyecto['titulo'] = celdas[2].get_text(strip=True)
                        
                        if proyecto.get('boletin'):
                            proyectos.append(proyecto)
            else:
                # Buscar enlaces alternativos
                enlaces = soup.find_all('a', href=re.compile('tramitacion\\.aspx\\?prmID=\\d+'))
                for enlace in enlaces[:20]:  # Limitar a 20 proyectos
                    href = enlace.get('href', '')
                    match = re.search(r'prmBOLETIN=(\d{4,5}-\d{2})', href)
                    if match:
                        # Construir URL correcta
                        if href.startswith('http'):
                            url_completa = href
                        elif href.startswith('/'):
                            url_completa = self.base_url + href
                        else:
                            url_completa = self.base_url + '/legislacion/ProyectosDeLey/' + href
                        
                        proyecto = {
                            'boletin': match.group(1),
                            'url_detalle': url_completa,
                            'titulo': enlace.get_text(strip=True)
                        }
                        proyectos.append(proyecto)
            
            return proyectos
            
        except Exception as e:
            logger.error(f"Error buscando proyectos recientes: {e}")
            return []
    
    def _buscar_proyectos_camara(self, fecha: datetime) -> List[Dict]:
        """
        Busca proyectos en el sitio del Congreso Nacional
        """
        try:
            # Hacer búsqueda por fecha específica
            response = self.session.get(self.search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer valores del formulario
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            viewstate_value = viewstate['value'] if viewstate else ''
            
            viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
            viewstate_generator_value = viewstate_generator['value'] if viewstate_generator else ''
            
            event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})
            event_validation_value = event_validation['value'] if event_validation else ''
            
            # Preparar datos del formulario para búsqueda específica por fecha
            fecha_str = fecha.strftime('%d/%m/%Y')
            form_data = {
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate_value,
                '__VIEWSTATEGENERATOR': viewstate_generator_value,
                '__EVENTVALIDATION': event_validation_value,
                'ctl00$mainPlaceHolder$txtFechaDesde': fecha_str,
                'ctl00$mainPlaceHolder$txtFechaHasta': fecha_str,  # Mismo día
                'ctl00$mainPlaceHolder$btnBuscar': 'Buscar'
            }
            
            # Realizar búsqueda
            response = self.session.post(self.search_url, data=form_data)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            proyectos = []
            
            # Buscar proyectos en la respuesta
            # Primero intentar tabla de resultados
            tabla = soup.find('table', {'id': 'mainPlaceHolder_grvResultado'})
            
            if tabla:
                filas = tabla.find_all('tr')[1:]  # Saltar header
                for fila in filas:
                    proyecto = self._extraer_proyecto_de_fila(fila, fecha)
                    if proyecto:
                        proyectos.append(proyecto)
            else:
                # Buscar enlaces a proyectos
                enlaces = soup.find_all('a', href=re.compile('tramitacion\\.aspx\\?prmID=\\d+'))
                for enlace in enlaces:
                    proyecto = self._extraer_proyecto_de_enlace(enlace, fecha)
                    if proyecto:
                        proyectos.append(proyecto)
            
            return proyectos
            
        except Exception as e:
            logger.error(f"Error buscando en Cámara: {e}")
            return []
    
    def _buscar_proyectos_senado(self, fecha: datetime) -> List[Dict]:
        """
        Busca proyectos en el sitio del Senado
        """
        # Por ahora retornamos vacío, se puede implementar después si es necesario
        return []
    
    def _extraer_proyecto_de_fila(self, fila, fecha: datetime) -> Dict:
        """
        Extrae información de proyecto desde una fila de tabla
        """
        try:
            celdas = fila.find_all('td')
            if len(celdas) < 3:
                return None
            
            proyecto = {
                'fecha_ingreso': fecha.strftime('%d/%m/%Y'),
                'origen': 'Congreso Nacional'
            }
            
            # Extraer boletín
            if celdas[0].find('a'):
                link = celdas[0].find('a')
                texto = link.get_text(strip=True)
                match = re.search(r'(\d{4,5}-\d{2})', texto)
                if match:
                    proyecto['boletin'] = match.group(1)
                    proyecto['url_detalle'] = self.base_url + link.get('href', '')
            
            # Extraer título
            if len(celdas) > 2:
                proyecto['titulo'] = celdas[2].get_text(strip=True)
            
            # Extraer estado
            if len(celdas) > 3:
                proyecto['estado'] = celdas[3].get_text(strip=True)
            
            return proyecto if proyecto.get('boletin') else None
            
        except Exception as e:
            logger.error(f"Error extrayendo proyecto de fila: {e}")
            return None
    
    def _extraer_proyecto_de_enlace(self, enlace, fecha: datetime) -> Dict:
        """
        Extrae información de proyecto desde un enlace
        """
        try:
            href = enlace.get('href', '')
            texto = enlace.get_text(strip=True)
            
            # Buscar boletín
            match = re.search(r'(\d{4,5}-\d{2})', href) or re.search(r'(\d{4,5}-\d{2})', texto)
            if not match:
                return None
            
            proyecto = {
                'boletin': match.group(1),
                'fecha_ingreso': fecha.strftime('%d/%m/%Y'),
                'origen': 'Congreso Nacional'
            }
            
            # Construir URL
            if href.startswith('/'):
                proyecto['url_detalle'] = self.base_url + href
            elif href.startswith('tramitacion'):
                proyecto['url_detalle'] = self.base_url + '/legislacion/ProyectosDeLey/' + href
            
            # Buscar título en el contexto
            parent = enlace.parent
            if parent:
                for elem in parent.find_all(string=True):
                    texto = elem.strip()
                    if len(texto) > 30 and not any(x in texto.lower() for x in ['boletín', 'fecha', 'ver']):
                        proyecto['titulo'] = texto
                        break
            
            return proyecto
            
        except Exception as e:
            logger.error(f"Error extrayendo proyecto de enlace: {e}")
            return None
    
    def obtener_detalle_proyecto(self, proyecto: Dict) -> Dict:
        """
        Enriquece el proyecto con información adicional y extrae contenido del documento
        """
        if not proyecto.get('url_detalle'):
            return proyecto
        
        try:
            response = self.session.get(proyecto['url_detalle'])
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar fecha de ingreso correcta
            fecha_elem = soup.find(string=re.compile('Fecha de ingreso'))
            if fecha_elem:
                parent = fecha_elem.parent
                if parent:
                    # Buscar el texto siguiente que contenga la fecha
                    siguiente = parent.find_next_sibling() or parent.find_next()
                    if siguiente:
                        fecha_texto = siguiente.get_text(strip=True)
                        # Extraer fecha en formato día mes año
                        match_fecha = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', fecha_texto)
                        if match_fecha:
                            dia = match_fecha.group(1).zfill(2)
                            mes_nombre = match_fecha.group(2).lower()
                            año = match_fecha.group(3)
                            
                            # Convertir mes a número
                            meses = {
                                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                            }
                            mes = meses.get(mes_nombre, '01')
                            proyecto['fecha_ingreso'] = f"{dia}/{mes}/{año}"
            
            # Buscar enlace al documento PDF - buscar específicamente el documento de INICIATIVA
            enlaces_doc = soup.find_all('a', href=re.compile('verDoc\\.aspx'))
            url_documento_encontrada = None
            
            for enlace in enlaces_doc:
                href = enlace.get('href', '')
                # Buscar específicamente el documento de iniciativa o que tenga prmID válido
                if 'INICIATIVA' in href.upper() or (
                    'prmID=' in href and 
                    not 'prmId=0' in href and 
                    'TABLASEMANAL' not in href.upper()
                ):
                    url_documento_encontrada = href
                    break
            
            # Si no encontramos un enlace específico, buscar en el texto "Ver" que esté cerca de "Documento"
            if not url_documento_encontrada:
                for enlace in enlaces_doc:
                    texto_cercano = enlace.get_text(strip=True)
                    if texto_cercano.lower() == 'ver':
                        # Verificar si está cerca de la palabra "documento" o "mensaje"
                        parent = enlace.parent
                        if parent and ('documento' in parent.get_text().lower() or 'mensaje' in parent.get_text().lower()):
                            url_documento_encontrada = enlace.get('href', '')
                            break
            
            if url_documento_encontrada:
                if url_documento_encontrada.startswith('/'):
                    url_documento_encontrada = self.base_url + url_documento_encontrada
                elif not url_documento_encontrada.startswith('http'):
                    url_documento_encontrada = self.base_url + '/' + url_documento_encontrada
                
                proyecto['url_documento'] = url_documento_encontrada
                
                # Descargar y extraer contenido del PDF
                contenido = self._extraer_contenido_pdf(url_documento_encontrada)
                if contenido:
                    proyecto['contenido_documento'] = contenido
                    # Generar resumen del contenido
                    proyecto['resumen'] = self._generar_resumen_proyecto(contenido, proyecto.get('titulo', ''))
            
            # Buscar urgencia
            urgencia = soup.find(string=re.compile('Urgencia'))
            if urgencia:
                proyecto['urgencia'] = True
            
            # Buscar comisión
            comision = soup.find(string=re.compile('Comisión'))
            if comision:
                siguiente = comision.find_next()
                if siguiente:
                    proyecto['comision'] = siguiente.get_text(strip=True)[:50]
            
        except Exception as e:
            logger.error(f"Error obteniendo detalle del proyecto: {e}")
        
        return proyecto
    
    def _extraer_contenido_pdf(self, url: str) -> Optional[str]:
        """
        Descarga y extrae el contenido completo de un PDF
        """
        try:
            # Descargar el PDF
            logger.info(f"Descargando PDF de: {url}")
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                # Siempre usar pypdf primero porque funciona mejor con estos PDFs
                try:
                    import io
                    from pypdf import PdfReader
                    
                    pdf_file = io.BytesIO(response.content)
                    reader = PdfReader(pdf_file)
                    
                    texto = ""
                    # Extraer hasta 5 páginas para tener contenido suficiente
                    max_paginas = min(5, len(reader.pages))
                    logger.info(f"Extrayendo {max_paginas} páginas del PDF")
                    
                    for i in range(max_paginas):
                        pagina_texto = reader.pages[i].extract_text()
                        if pagina_texto:
                            texto += pagina_texto + "\n\n"
                    
                    if texto and len(texto) > 50:  # Verificar que hay contenido útil
                        logger.info(f"Extraídos {len(texto)} caracteres del PDF")
                        # Retornar hasta 5000 caracteres para tener suficiente contexto
                        return texto[:5000] if len(texto) > 5000 else texto
                        
                except Exception as e:
                    logger.error(f"Error con pypdf: {e}")
                    
                # Fallback: usar pdf_extractor si pypdf falla
                if pdf_extractor:
                    try:
                        texto, metodo = pdf_extractor.extract_text(response.content, max_pages=5)
                        if texto and len(texto) > 50:
                            logger.info(f"Extraídos {len(texto)} caracteres con pdf_extractor")
                            return texto[:5000] if len(texto) > 5000 else texto
                    except Exception as e:
                        logger.error(f"Error con pdf_extractor: {e}")
            else:
                logger.error(f"Error descargando PDF: Status {response.status_code}")
                        
        except Exception as e:
            logger.error(f"Error descargando PDF de {url}: {e}")
        
        return None
    
    def _generar_resumen_proyecto(self, contenido: str, titulo: str) -> str:
        """
        Genera un resumen inteligente del proyecto usando IA
        """
        if not contenido:
            return titulo[:300] if len(titulo) <= 300 else titulo[:297] + '...'
        
        try:
            # Si el contenido es muy largo, usar solo las primeras 4000 caracteres
            contenido_para_resumen = contenido[:4000] if len(contenido) > 4000 else contenido
            
            # Usar OpenAI para generar un resumen inteligente
            try:
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                
                prompt = f"""Analiza el siguiente proyecto de ley y genera un resumen conciso y claro de máximo 250 caracteres.
                
El resumen debe explicar:
1. Qué propone o modifica el proyecto
2. El objetivo principal
3. Los aspectos más relevantes

Título del proyecto: {titulo}

Contenido del proyecto:
{contenido_para_resumen}

IMPORTANTE: 
- El resumen debe ser en español
- Máximo 250 caracteres
- Debe ser claro y directo
- No incluyas el número de boletín
- Enfócate en lo esencial del proyecto

Resumen:"""

                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Eres un experto analista legislativo chileno. Tu tarea es crear resúmenes concisos y claros de proyectos de ley."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.3
                )
                
                resumen = response.choices[0].message.content.strip()
                
                # Asegurar que no exceda 300 caracteres
                if len(resumen) > 300:
                    resumen = resumen[:297] + '...'
                
                logger.info(f"Resumen generado por IA para: {titulo[:50]}...")
                return resumen
                
            except Exception as e:
                logger.error(f"Error con OpenAI: {e}")
                # Fallback: usar método simple si falla la IA
                return self._generar_resumen_simple(contenido, titulo)
                
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return titulo[:300] if len(titulo) <= 300 else titulo[:297] + '...'
    
    def _generar_resumen_simple(self, contenido: str, titulo: str) -> str:
        """
        Método de fallback para generar resumen sin IA
        """
        # Limpiar el contenido
        contenido_limpio = contenido.replace('\n', ' ').replace('  ', ' ')
        
        # Buscar FUNDAMENTOS
        fundamentos_match = re.search(r'FUNDAMENTO[S]?\s*([^.]+\.(?:[^.]+\.)?)', contenido_limpio, re.IGNORECASE)
        if fundamentos_match:
            resumen = fundamentos_match.group(1).strip()
            if len(resumen) > 300:
                resumen = resumen[:297] + '...'
            return resumen
        
        # Si no hay fundamentos, tomar el primer párrafo sustancial
        parrafos = contenido.split('\n\n')
        for parrafo in parrafos:
            if len(parrafo) > 50 and not parrafo.isupper() and 'Boletín' not in parrafo:
                resumen = parrafo.strip()[:300]
                if len(parrafo) > 300:
                    resumen = resumen[:297] + '...'
                return resumen
        
        return titulo[:300] if len(titulo) <= 300 else titulo[:297] + '...'
    
    def generar_resumen(self, proyecto: Dict) -> str:
        """
        Genera un resumen conciso del proyecto
        """
        # Si tenemos un resumen extraído del documento, usarlo
        if proyecto.get('resumen'):
            return proyecto['resumen']
        
        # Fallback: usar el título
        titulo = proyecto.get('titulo', 'Sin título')
        if len(titulo) > 300:
            titulo = titulo[:297] + '...'
        
        return titulo


def test_scraper():
    """
    Función de prueba
    """
    scraper = ScraperProyectosLeyIntegrado()
    
    # Para pruebas, buscar proyectos de ayer
    proyectos = scraper.obtener_proyectos_dia_anterior()
    
    print(f"\n=== PROYECTOS DE LEY DEL DÍA ANTERIOR ===")
    print(f"Total: {len(proyectos)} proyectos\n")
    
    for i, proyecto in enumerate(proyectos, 1):
        # Enriquecer con detalles
        proyecto = scraper.obtener_detalle_proyecto(proyecto)
        
        print(f"{i}. {scraper.generar_resumen(proyecto)}")
        print(f"   Fecha: {proyecto.get('fecha_ingreso', 'Sin fecha')}")
        print(f"   Origen: {proyecto.get('origen', 'Sin origen')}")
        print()
    
    return proyectos


if __name__ == "__main__":
    test_scraper()