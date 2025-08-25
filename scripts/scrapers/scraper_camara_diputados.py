#!/usr/bin/env python3
"""
Scraper para obtener proyectos de ley de la Cámara de Diputados de Chile
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperCamaraDiputados:
    def __init__(self):
        self.base_url = "https://www.camara.cl"
        self.search_url = f"{self.base_url}/legislacion/proyectosdeley/proyectos_ley.aspx"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
    def obtener_proyectos_recientes(self, dias_atras: int = 1) -> List[Dict]:
        """
        Obtiene los proyectos de ley de los últimos días
        """
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=dias_atras)
        
        logger.info(f"Buscando proyectos desde {fecha_desde.strftime('%d/%m/%Y')} hasta {fecha_hasta.strftime('%d/%m/%Y')}")
        
        try:
            # Primero obtener la página para capturar viewstate
            response = self.session.get(self.search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer valores del formulario
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            viewstate_value = viewstate['value'] if viewstate else ''
            
            viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
            viewstate_generator_value = viewstate_generator['value'] if viewstate_generator else ''
            
            event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})
            event_validation_value = event_validation['value'] if event_validation else ''
            
            # Preparar datos del formulario
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
            
            # Realizar búsqueda
            response = self.session.post(self.search_url, data=form_data)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tabla de resultados
            tabla = soup.find('table', {'id': 'mainPlaceHolder_grvResultado'})
            
            if not tabla:
                logger.warning("No se encontró tabla de resultados")
                # Intentar buscar proyectos en otro formato
                return self._buscar_proyectos_alternativos(soup)
            
            proyectos = []
            filas = tabla.find_all('tr')[1:]  # Saltar header
            
            for fila in filas:
                celdas = fila.find_all('td')
                if len(celdas) >= 4:
                    proyecto = self._extraer_info_proyecto(celdas)
                    if proyecto:
                        proyectos.append(proyecto)
            
            logger.info(f"Se encontraron {len(proyectos)} proyectos")
            return proyectos
            
        except Exception as e:
            logger.error(f"Error obteniendo proyectos: {e}")
            return []
    
    def _extraer_info_proyecto(self, celdas) -> Optional[Dict]:
        """
        Extrae información de un proyecto desde las celdas de la tabla
        """
        try:
            proyecto = {}
            
            # Boletín (número del proyecto)
            if len(celdas) > 0:
                boletin = celdas[0].get_text(strip=True)
                proyecto['boletin'] = boletin
                
                # Buscar enlace al detalle
                link = celdas[0].find('a')
                if link:
                    proyecto['url_detalle'] = self.base_url + link.get('href', '')
            
            # Fecha de ingreso
            if len(celdas) > 1:
                proyecto['fecha_ingreso'] = celdas[1].get_text(strip=True)
            
            # Título/materia
            if len(celdas) > 2:
                proyecto['titulo'] = celdas[2].get_text(strip=True)
            
            # Estado/etapa
            if len(celdas) > 3:
                proyecto['estado'] = celdas[3].get_text(strip=True)
            
            # Cámara de origen
            if len(celdas) > 4:
                proyecto['origen'] = celdas[4].get_text(strip=True)
                
            return proyecto if proyecto.get('boletin') else None
            
        except Exception as e:
            logger.error(f"Error extrayendo proyecto: {e}")
            return None
    
    def _buscar_proyectos_alternativos(self, soup) -> List[Dict]:
        """
        Búsqueda alternativa de proyectos si no se encuentra la tabla principal
        """
        proyectos = []
        
        # Buscar todos los enlaces a tramitación de proyectos
        enlaces_proyecto = soup.find_all('a', href=re.compile('tramitacion\\.aspx\\?prmID=\\d+'))
        
        for enlace in enlaces_proyecto:
            proyecto = {}
            
            # Obtener el texto del enlace que generalmente contiene el boletín
            texto = enlace.get_text(strip=True)
            
            # Buscar el boletín en el texto o en el href
            href = enlace.get('href', '')
            match_boletin = re.search(r'(\d{4,5}-\d{2})', href) or re.search(r'(\d{4,5}-\d{2})', texto)
            if match_boletin:
                proyecto['boletin'] = match_boletin.group(1)
            
            # Obtener el título del proyecto
            # Buscar en el elemento padre o hermanos
            parent = enlace.parent
            if parent:
                # Buscar texto que parezca un título (más de 20 caracteres)
                for elem in parent.find_all(text=True):
                    texto_limpio = elem.strip()
                    if len(texto_limpio) > 20 and not texto_limpio.startswith('Boletín'):
                        proyecto['titulo'] = texto_limpio
                        break
            
            # Construir URL correcta
            if href.startswith('/'):
                proyecto['url_detalle'] = self.base_url + href
            elif href.startswith('tramitacion'):
                proyecto['url_detalle'] = self.base_url + '/legislacion/ProyectosDeLey/' + href
            else:
                proyecto['url_detalle'] = href
            
            if proyecto.get('boletin'):
                proyectos.append(proyecto)
        
        return proyectos
    
    def obtener_detalle_proyecto(self, url_detalle: str) -> Dict:
        """
        Obtiene el detalle completo de un proyecto, incluyendo documentos
        """
        try:
            response = self.session.get(url_detalle)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            detalle = {}
            
            # Buscar fecha de ingreso
            fecha_elem = soup.find(string=re.compile('Fecha de ingreso'))
            if fecha_elem:
                fecha_texto = fecha_elem.find_next().get_text(strip=True) if fecha_elem.find_next() else ''
                detalle['fecha_ingreso'] = fecha_texto
            
            # Buscar estado/etapa
            etapa_elem = soup.find(string=re.compile('trámite constitucional'))
            if etapa_elem:
                detalle['estado'] = etapa_elem.strip()
            
            # Buscar autores
            autores_elem = soup.find(string=re.compile('Autor'))
            if autores_elem:
                parent = autores_elem.parent
                if parent:
                    # Buscar los nombres de los autores en el contenedor
                    nombres = []
                    for elem in parent.find_next_siblings()[:5]:
                        texto = elem.get_text(strip=True)
                        if texto and not any(x in texto.lower() for x in ['fecha', 'boletín', 'cámara']):
                            nombres.append(texto)
                    if nombres:
                        detalle['autores'] = ', '.join(nombres[:5])
            
            # Buscar cámara de origen
            camara_elem = soup.find(string=re.compile('Cámara de origen'))
            if camara_elem:
                camara_texto = camara_elem.find_next().get_text(strip=True) if camara_elem.find_next() else ''
                detalle['origen'] = camara_texto
            
            # Buscar descripción/materia
            materia_elem = soup.find('div', class_='proyecto-descripcion') or soup.find('div', class_='materia')
            if materia_elem:
                detalle['descripcion'] = materia_elem.get_text(strip=True)[:500]
            
            # Buscar enlaces a documentos (especialmente el documento principal)
            documentos = []
            
            # Buscar enlaces con "verDoc.aspx"
            links_doc = soup.find_all('a', href=re.compile('verDoc\\.aspx'))
            for link in links_doc[:2]:
                doc = {
                    'nombre': link.get_text(strip=True) or 'Documento principal',
                    'url': self.base_url + link.get('href', '') if link.get('href', '').startswith('/') else link.get('href', '')
                }
                documentos.append(doc)
            
            # También buscar PDFs directos
            links_pdf = soup.find_all('a', href=re.compile(r'\.pdf', re.I))
            for link in links_pdf[:2]:
                doc = {
                    'nombre': link.get_text(strip=True) or 'Documento PDF',
                    'url': self.base_url + link.get('href', '') if not link.get('href', '').startswith('http') else link.get('href', '')
                }
                if doc not in documentos:
                    documentos.append(doc)
            
            detalle['documentos'] = documentos
            
            return detalle
            
        except Exception as e:
            logger.error(f"Error obteniendo detalle del proyecto: {e}")
            return {}
    
    def generar_resumen(self, proyecto: Dict) -> str:
        """
        Genera un resumen del proyecto para el informe
        """
        resumen_parts = []
        
        # Título y boletín
        if proyecto.get('titulo'):
            resumen_parts.append(f"Proyecto {proyecto.get('boletin', 'S/N')}: {proyecto['titulo']}")
        
        # Estado
        if proyecto.get('estado'):
            resumen_parts.append(f"Estado: {proyecto['estado']}")
        
        # Origen
        if proyecto.get('origen'):
            resumen_parts.append(f"Origen: {proyecto['origen']}")
        
        # Descripción breve
        if proyecto.get('descripcion'):
            desc_corta = proyecto['descripcion'][:200] + "..." if len(proyecto['descripcion']) > 200 else proyecto['descripcion']
            resumen_parts.append(desc_corta)
        
        return " | ".join(resumen_parts) if resumen_parts else "Sin información disponible"


def test_scraper():
    """
    Función de prueba
    """
    scraper = ScraperCamaraDiputados()
    
    # Buscar proyectos de los últimos 7 días para prueba
    proyectos = scraper.obtener_proyectos_recientes(dias_atras=7)
    
    print(f"\n=== PROYECTOS DE LEY ENCONTRADOS ===")
    print(f"Total: {len(proyectos)} proyectos\n")
    
    for i, proyecto in enumerate(proyectos[:5], 1):
        print(f"{i}. Boletín: {proyecto.get('boletin', 'N/A')}")
        print(f"   Título: {proyecto.get('titulo', 'Sin título')}")
        print(f"   Fecha: {proyecto.get('fecha_ingreso', 'Sin fecha')}")
        print(f"   Estado: {proyecto.get('estado', 'Sin estado')}")
        
        # Si hay URL de detalle, obtener más información
        if proyecto.get('url_detalle'):
            detalle = scraper.obtener_detalle_proyecto(proyecto['url_detalle'])
            if detalle.get('documentos'):
                print(f"   Documentos: {len(detalle['documentos'])} disponibles")
        
        print(f"   Resumen: {scraper.generar_resumen(proyecto)}")
        print()
    
    return proyectos


if __name__ == "__main__":
    test_scraper()