#!/usr/bin/env python3
"""
Scraper integrado para proyectos de ley del día anterior
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import List, Dict
import re

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
    
    def obtener_proyectos_dia_anterior(self) -> List[Dict]:
        """
        Obtiene solo los proyectos ingresados el día anterior
        """
        # Calcular fecha del día anterior
        ayer = datetime.now() - timedelta(days=1)
        fecha_busqueda = ayer.strftime('%d/%m/%Y')
        
        logger.info(f"Buscando proyectos del {fecha_busqueda}")
        
        proyectos = []
        
        # Buscar en Cámara de Diputados
        proyectos_camara = self._buscar_proyectos_camara(ayer)
        proyectos.extend(proyectos_camara)
        
        # Buscar en Senado (si es necesario)
        proyectos_senado = self._buscar_proyectos_senado(ayer)
        proyectos.extend(proyectos_senado)
        
        # Eliminar duplicados por boletín
        proyectos_unicos = {}
        for p in proyectos:
            if p.get('boletin'):
                proyectos_unicos[p['boletin']] = p
        
        proyectos_filtrados = list(proyectos_unicos.values())
        
        logger.info(f"Total proyectos del {fecha_busqueda}: {len(proyectos_filtrados)}")
        
        return proyectos_filtrados
    
    def _buscar_proyectos_camara(self, fecha: datetime) -> List[Dict]:
        """
        Busca proyectos en el sitio de la Cámara de Diputados
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
                'origen': 'Cámara de Diputados'
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
                'origen': 'Cámara de Diputados'
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
        Enriquece el proyecto con información adicional
        """
        if not proyecto.get('url_detalle'):
            return proyecto
        
        try:
            response = self.session.get(proyecto['url_detalle'])
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar autores
            autores = []
            for texto in soup.find_all(string=re.compile('Autor')):
                parent = texto.parent
                if parent:
                    siguiente = parent.find_next_sibling()
                    if siguiente:
                        autores_texto = siguiente.get_text(strip=True)
                        if autores_texto:
                            autores = [a.strip() for a in autores_texto.split(',')][:3]
                            break
            
            if autores:
                proyecto['autores'] = ', '.join(autores) + ('...' if len(autores) > 3 else '')
            
            # Buscar urgencia
            urgencia = soup.find(string=re.compile('Urgencia'))
            if urgencia:
                proyecto['urgencia'] = True
            
            # Buscar materia/comisión
            comision = soup.find(string=re.compile('Comisión'))
            if comision:
                siguiente = comision.find_next()
                if siguiente:
                    proyecto['comision'] = siguiente.get_text(strip=True)[:50]
            
        except Exception as e:
            logger.debug(f"No se pudo obtener detalle adicional: {e}")
        
        return proyecto
    
    def generar_resumen(self, proyecto: Dict) -> str:
        """
        Genera un resumen conciso del proyecto
        """
        partes = []
        
        # Título principal
        titulo = proyecto.get('titulo', 'Sin título')
        if len(titulo) > 150:
            titulo = titulo[:147] + '...'
        partes.append(f"Boletín {proyecto.get('boletin', 'S/N')}: {titulo}")
        
        # Autores si existen
        if proyecto.get('autores'):
            partes.append(f"Autores: {proyecto['autores']}")
        
        # Urgencia si existe
        if proyecto.get('urgencia'):
            partes.append("Con urgencia")
        
        # Comisión si existe
        if proyecto.get('comision'):
            partes.append(f"Comisión: {proyecto['comision']}")
        
        return ' | '.join(partes)


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