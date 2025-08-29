#!/usr/bin/env python3
"""
Scraper SEA usando la URL correcta: buscarProyectoResumen.php
Esta es la página donde realmente están los proyectos
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ScraperSEACorrecto:
    def __init__(self):
        """Inicializa el scraper con la URL CORRECTA"""
        self.base_url = "https://seia.sea.gob.cl"
        # URL CORRECTA donde están los proyectos
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoResumen.php"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Referer': 'https://seia.sea.gob.cl/busqueda/buscarProyecto.php'
        })
    
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos REALES del SEA de los últimos días
        """
        logger.info(f"🎯 Obteniendo proyectos del SEA desde {self.search_url}")
        
        proyectos_totales = []
        proyectos_ids = set()
        
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=dias_atras)
        
        # Estrategia 1: Buscar con parámetros GET
        proyectos = self._buscar_proyectos_get(fecha_desde, fecha_hasta)
        for p in proyectos:
            if p.get('id') not in proyectos_ids:
                proyectos_totales.append(p)
                proyectos_ids.add(p.get('id'))
        
        # Estrategia 2: Buscar con POST
        if len(proyectos_totales) < 5:  # Si hay menos de 5 proyectos, intentar POST
            logger.info("🔄 Intentando búsqueda POST...")
            proyectos = self._buscar_proyectos_post(fecha_desde, fecha_hasta)
            for p in proyectos:
                if p.get('id') not in proyectos_ids:
                    proyectos_totales.append(p)
                    proyectos_ids.add(p.get('id'))
        
        logger.info(f"✅ Total proyectos encontrados: {len(proyectos_totales)}")
        
        # Verificar proyectos del 26/08
        self._verificar_proyectos_26_agosto(proyectos_totales)
        
        return proyectos_totales
    
    def _buscar_proyectos_get(self, fecha_desde: datetime, fecha_hasta: datetime) -> List[Dict]:
        """Busca proyectos usando GET con parámetros en la URL"""
        proyectos = []
        
        try:
            # Parámetros como los viste en la URL
            params = {
                'tipoPresentacion': 'AMBOS',  # DIA y EIA
                'PresentacionMin': fecha_desde.strftime('%d/%m/%Y'),
                'PresentacionMax': fecha_hasta.strftime('%d/%m/%Y')
            }
            
            logger.info(f"🔍 Buscando con GET: {params}")
            
            response = self.session.get(
                self.search_url,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Respuesta obtenida ({len(response.text)} caracteres)")
                proyectos = self._extraer_proyectos_html(response.text)
            else:
                logger.error(f"❌ Error HTTP: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error en búsqueda GET: {e}")
        
        return proyectos
    
    def _buscar_proyectos_post(self, fecha_desde: datetime, fecha_hasta: datetime) -> List[Dict]:
        """Busca proyectos usando POST"""
        proyectos = []
        
        try:
            # Primero obtener la página para conseguir cookies
            logger.info("🍪 Obteniendo cookies...")
            resp = self.session.get(f"{self.base_url}/busqueda/buscarProyecto.php")
            
            # Headers específicos para el POST
            self.session.headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://seia.sea.gob.cl',
                'Referer': 'https://seia.sea.gob.cl/busqueda/buscarProyecto.php'
            })
            
            # Datos del formulario - Usar exactamente los campos del formulario
            data = {
                'nombre': '',
                'titular': '',
                'folio': '',
                'tipoPresentacion': 'AMBOS',
                'PresentacionMin': fecha_desde.strftime('%d/%m/%Y'),
                'PresentacionMax': fecha_hasta.strftime('%d/%m/%Y'),
                'CalificaMin': '',
                'CalificaMax': '',
                'buscar': 'Buscar'  # Este es importante
            }
            
            logger.info(f"🔍 Buscando con POST del {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}")
            logger.info(f"📮 URL POST: {self.search_url}")
            logger.info(f"📋 Datos: {data}")
            
            response = self.session.post(
                self.search_url,
                data=data,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Respuesta POST obtenida ({len(response.text)} caracteres)")
                proyectos = self._extraer_proyectos_html(response.text)
            else:
                logger.error(f"❌ Error HTTP en POST: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error en búsqueda POST: {e}")
        
        return proyectos
    
    def _extraer_proyectos_html(self, html_content: str) -> List[Dict]:
        """Extrae proyectos desde el HTML de la respuesta"""
        proyectos = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar la tabla de resultados
            tablas = soup.find_all('table')
            logger.info(f"📊 Tablas encontradas: {len(tablas)}")
            
            for tabla in tablas:
                # Buscar si es la tabla de proyectos
                # Generalmente tiene headers como "Nombre", "Tipo", "Titular", etc.
                headers = tabla.find_all('th')
                header_text = ' '.join([th.get_text().strip().lower() for th in headers])
                
                # Si hay headers o si la tabla tiene muchas filas, procesarla
                if (any(palabra in header_text for palabra in ['nombre', 'tipo', 'titular', 'proyecto']) or 
                    len(tabla.find_all('tr')) > 5):
                    
                    filas = tabla.find_all('tr')
                    
                    # Si no hay headers pero hay filas, también procesar
                    if len(filas) > 1:
                        logger.info(f"✅ Tabla encontrada con {len(filas)} filas")
                        
                        # Determinar si la primera fila es header
                        primera_fila = filas[0]
                        es_header = len(primera_fila.find_all('th')) > 0 or 'nombre' in primera_fila.get_text().lower()
                        
                        filas_datos = filas[1:] if es_header else filas
                        logger.info(f"📋 Procesando {len(filas_datos)} filas de datos")
                    
                        for i, fila in enumerate(filas_datos, 1):
                            proyecto = self._extraer_proyecto_de_fila(fila)
                            if proyecto:
                                proyectos.append(proyecto)
                                logger.debug(f"   ✅ Proyecto: {proyecto.get('titulo', '')[:50]}")
                            
                            # Log cada 10 filas
                            if i % 10 == 0:
                                logger.info(f"   Procesadas {i} filas, {len(proyectos)} proyectos encontrados...")
            
            # Si no hay tablas, buscar en divs con clase resultado
            if not proyectos:
                logger.info("🔍 Buscando en elementos div...")
                resultados = soup.find_all('div', class_=re.compile('resultado|proyecto|item'))
                
                for resultado in resultados[:100]:  # Limitar a 100
                    proyecto = self._extraer_proyecto_de_div(resultado)
                    if proyecto:
                        proyectos.append(proyecto)
            
            logger.info(f"✅ Total proyectos extraídos del HTML: {len(proyectos)}")
            
        except Exception as e:
            logger.error(f"Error extrayendo proyectos del HTML: {e}")
        
        return proyectos
    
    def _extraer_proyecto_de_fila(self, fila) -> Optional[Dict]:
        """Extrae un proyecto desde una fila de tabla"""
        try:
            celdas = fila.find_all('td')
            if len(celdas) < 2:
                return None
            
            proyecto = {
                'fuente': 'SEA',
                'fecha_extraccion': datetime.now().isoformat()
            }
            
            # Mapeo típico de columnas en la tabla del SEA
            # Columna 0: Nombre/Título con enlace
            # Columna 1: Tipo (DIA/EIA)
            # Columna 2: Titular/Empresa
            # Columna 3: Región
            # Columna 4: Comuna
            # Columna 5: Estado
            # Columna 6: Fecha presentación
            # Columna 7: Fecha calificación
            
            for i, celda in enumerate(celdas):
                texto = celda.get_text(strip=True)
                
                # Columna 0: Nombre del proyecto
                if i == 0:
                    proyecto['titulo'] = texto
                    # Buscar enlace
                    enlace = celda.find('a')
                    if enlace:
                        href = enlace.get('href', '')
                        proyecto['url'] = urljoin(self.base_url, href)
                        # Extraer ID del enlace
                        id_match = re.search(r'id_expediente=(\d+)', href)
                        if id_match:
                            proyecto['id'] = id_match.group(1)
                        else:
                            # Intentar con otro patrón
                            id_match = re.search(r'id=(\d+)', href)
                            if id_match:
                                proyecto['id'] = id_match.group(1)
                
                # Columna 1: Tipo
                elif i == 1 and texto in ['DIA', 'EIA']:
                    proyecto['tipo'] = texto
                
                # Columna 2: Titular
                elif i == 2 and len(texto) > 2:
                    proyecto['empresa'] = texto
                
                # Columna 3: Región
                elif i == 3 and ('región' in texto.lower() or 'metropolitana' in texto.lower()):
                    proyecto['region'] = texto
                
                # Columna 4: Comuna
                elif i == 4 and len(texto) > 2:
                    proyecto['comuna'] = texto
                
                # Columna 5: Estado
                elif i == 5:
                    proyecto['estado'] = texto
                
                # Columna 6 o 7: Fechas
                elif i in [6, 7]:
                    fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
                    if fecha_match:
                        fecha = fecha_match.group(1).replace('-', '/')
                        if i == 6:
                            proyecto['fecha_presentacion'] = fecha
                        else:
                            proyecto['fecha_calificacion'] = fecha
            
            # Validar que el proyecto tenga información mínima
            if proyecto.get('titulo') and len(proyecto.get('titulo', '')) > 5:
                # Generar ID si no lo tiene
                if not proyecto.get('id'):
                    proyecto['id'] = f"sea_{hash(proyecto['titulo']) % 1000000}"
                
                # Generar resumen
                proyecto['resumen'] = self._generar_resumen(proyecto)
                
                # Calcular relevancia
                proyecto['relevancia'] = self._calcular_relevancia(proyecto)
                
                return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de fila: {e}")
        
        return None
    
    def _extraer_proyecto_de_div(self, div) -> Optional[Dict]:
        """Extrae un proyecto desde un div"""
        try:
            proyecto = {
                'fuente': 'SEA',
                'fecha_extraccion': datetime.now().isoformat()
            }
            
            # Buscar título
            titulo_elem = div.find(['h2', 'h3', 'h4', 'a'])
            if titulo_elem:
                proyecto['titulo'] = titulo_elem.get_text(strip=True)
                if titulo_elem.name == 'a':
                    proyecto['url'] = urljoin(self.base_url, titulo_elem.get('href', ''))
            
            # Buscar otros datos en el texto
            texto_completo = div.get_text()
            
            # Tipo
            if 'DIA' in texto_completo:
                proyecto['tipo'] = 'DIA'
            elif 'EIA' in texto_completo:
                proyecto['tipo'] = 'EIA'
            
            # Fecha
            fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto_completo)
            if fecha_match:
                proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
            
            # Empresa
            empresa_match = re.search(r'Titular:\s*([^\n,]+)', texto_completo)
            if empresa_match:
                proyecto['empresa'] = empresa_match.group(1).strip()
            
            # Región
            region_match = re.search(r'Región[:\s]*([^\n,]+)', texto_completo)
            if region_match:
                proyecto['region'] = region_match.group(1).strip()
            
            if proyecto.get('titulo') and len(proyecto.get('titulo', '')) > 5:
                proyecto['id'] = f"sea_{hash(proyecto['titulo']) % 1000000}"
                proyecto['resumen'] = self._generar_resumen(proyecto)
                proyecto['relevancia'] = self._calcular_relevancia(proyecto)
                return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de div: {e}")
        
        return None
    
    def _generar_resumen(self, proyecto: Dict) -> str:
        """Genera un resumen del proyecto"""
        tipo = proyecto.get('tipo', 'Proyecto')
        empresa = proyecto.get('empresa', 'N/A')
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        
        resumen = f"{tipo} presentado por {empresa}"
        
        if region:
            resumen += f" en {region}"
            if comuna:
                resumen += f", {comuna}"
        
        estado = proyecto.get('estado', '')
        if estado:
            resumen += f". Estado: {estado}"
        
        return resumen
    
    def _calcular_relevancia(self, proyecto: Dict) -> float:
        """Calcula la relevancia del proyecto (0-10)"""
        relevancia = 5.0
        
        # Por tipo
        if proyecto.get('tipo') == 'EIA':
            relevancia += 2
        elif proyecto.get('tipo') == 'DIA':
            relevancia += 1
        
        # Por estado
        estado = proyecto.get('estado', '').lower()
        if 'aprobado' in estado:
            relevancia += 1.5
        elif 'calificación' in estado:
            relevancia += 1
        
        # Por sector (basado en el título)
        titulo = proyecto.get('titulo', '').lower()
        
        # Sectores prioritarios
        if any(s in titulo for s in ['minera', 'minero', 'cobre', 'litio', 'oro']):
            relevancia += 2
        elif any(s in titulo for s in ['energía', 'solar', 'fotovoltaico', 'eólico']):
            relevancia += 1.5
        elif any(s in titulo for s in ['inmobiliario', 'residencial', 'habitacional']):
            relevancia += 1
        elif any(s in titulo for s in ['tratamiento', 'aguas', 'sanitario']):
            relevancia += 1
        
        return min(relevancia, 10)
    
    def _verificar_proyectos_26_agosto(self, proyectos: List[Dict]):
        """Verifica si encontramos los proyectos específicos del 26/08"""
        proyectos_buscados = [
            "Planta de Tratamiento de Aguas Servidas El Cerrillo",
            "Proyecto Inmobiliario Modificación Praderas de lo Aguirre",
            "Parque Solar Alvarado",
            "Central Fotovoltaica Sol del Sauzal"
        ]
        
        logger.info("🔍 Verificando proyectos del 26/08/2025:")
        
        for nombre_buscado in proyectos_buscados:
            encontrado = False
            proyecto_encontrado = None
            
            for p in proyectos:
                titulo = p.get('titulo', '').lower()
                # Buscar coincidencias parciales
                palabras_clave = nombre_buscado.lower().split()
                
                # Si al menos 2 palabras clave coinciden, considerarlo encontrado
                coincidencias = sum(1 for palabra in palabras_clave if palabra in titulo)
                
                if coincidencias >= 2 or nombre_buscado.lower() in titulo:
                    encontrado = True
                    proyecto_encontrado = p
                    break
            
            if encontrado:
                logger.info(f"   ✅ {nombre_buscado}")
                if proyecto_encontrado:
                    logger.info(f"      Título: {proyecto_encontrado.get('titulo', '')}")
                    logger.info(f"      Fecha: {proyecto_encontrado.get('fecha_presentacion', 'N/A')}")
            else:
                logger.info(f"   ❌ {nombre_buscado} (NO ENCONTRADO)")


def test_scraper():
    """Función de prueba del scraper"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "=" * 80)
    print("🎯 PRUEBA SCRAPER SEA - URL CORRECTA")
    print("=" * 80)
    
    scraper = ScraperSEACorrecto()
    
    # Probar con 7 días para incluir el 26/08
    proyectos = scraper.obtener_datos_sea(dias_atras=7)
    
    print(f"\n✅ Total proyectos encontrados: {len(proyectos)}")
    
    if proyectos:
        print("\n📋 PROYECTOS ENCONTRADOS:")
        print("-" * 80)
        
        # Mostrar todos los proyectos para verificar
        for i, p in enumerate(proyectos[:20], 1):
            print(f"\n{i}. {p.get('titulo', 'Sin título')}")
            print(f"   Tipo: {p.get('tipo', 'N/A')}")
            print(f"   Empresa: {p.get('empresa', 'N/A')}")
            print(f"   Fecha: {p.get('fecha_presentacion', 'N/A')}")
            print(f"   Región: {p.get('region', 'N/A')}")
            print(f"   Estado: {p.get('estado', 'N/A')}")
            print(f"   Relevancia: ⭐ {p.get('relevancia', 0):.1f}/10")
    else:
        print("\n⚠️ No se encontraron proyectos")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_scraper()