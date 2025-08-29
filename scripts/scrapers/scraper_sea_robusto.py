#!/usr/bin/env python3
"""
Scraper SEA ROBUSTO - Versión mejorada y optimizada
Obtiene proyectos reales del SEIA usando múltiples estrategias
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import re
import time
import json

logger = logging.getLogger(__name__)

class ScraperSEARobusto:
    def __init__(self):
        """Inicializa el scraper robusto del SEIA"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        self.base_url = "https://seia.sea.gob.cl"
        
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos del SEIA usando múltiples estrategias
        """
        todos_proyectos = []
        proyectos_unicos = {}
        
        logger.info(f"🌊 Iniciando scraper SEA robusto (últimos {dias_atras} días)")
        
        # Estrategia 1: Búsqueda por API JSON (si existe)
        proyectos_api = self._buscar_proyectos_api(dias_atras)
        for p in proyectos_api:
            key = p.get('titulo', '').lower()[:50]
            if key and key not in proyectos_unicos:
                proyectos_unicos[key] = p
        
        # Estrategia 2: Búsqueda directa en páginas de evaluación
        proyectos_evaluacion = self._obtener_proyectos_en_evaluacion()
        for p in proyectos_evaluacion:
            key = p.get('titulo', '').lower()[:50]
            if key and key not in proyectos_unicos:
                proyectos_unicos[key] = p
        
        # Estrategia 3: Búsqueda en proyectos aprobados recientes
        proyectos_aprobados = self._obtener_proyectos_aprobados_recientes(dias_atras)
        for p in proyectos_aprobados:
            key = p.get('titulo', '').lower()[:50]
            if key and key not in proyectos_unicos:
                proyectos_unicos[key] = p
        
        # Estrategia 4: Búsqueda por tabla de resultados
        proyectos_tabla = self._buscar_en_tabla_resultados(dias_atras)
        for p in proyectos_tabla:
            key = p.get('titulo', '').lower()[:50]
            if key and key not in proyectos_unicos:
                proyectos_unicos[key] = p
        
        # Convertir a lista y filtrar
        todos_proyectos = list(proyectos_unicos.values())
        
        # Filtrar solo proyectos reales (no noticias)
        proyectos_filtrados = self._filtrar_proyectos_reales(todos_proyectos)
        
        logger.info(f"✅ Total proyectos únicos encontrados: {len(proyectos_filtrados)}")
        
        return proyectos_filtrados[:50]  # Limitar a 50 proyectos
    
    def _buscar_proyectos_api(self, dias_atras: int) -> List[Dict]:
        """Busca proyectos usando endpoints API/JSON"""
        proyectos = []
        
        # Posibles endpoints de API
        endpoints = [
            f"{self.base_url}/api/proyectos/recientes",
            f"{self.base_url}/ws/proyectos/ultimos",
            f"{self.base_url}/json/proyectos",
            f"{self.base_url}/api/v1/proyectos/lista"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'json' in content_type:
                        data = response.json()
                        if isinstance(data, list):
                            for item in data:
                                proyecto = self._convertir_json_a_proyecto(item)
                                if proyecto:
                                    proyectos.append(proyecto)
                        elif isinstance(data, dict) and 'proyectos' in data:
                            for item in data['proyectos']:
                                proyecto = self._convertir_json_a_proyecto(item)
                                if proyecto:
                                    proyectos.append(proyecto)
                        logger.info(f"✅ API encontrada: {len(proyectos)} proyectos desde {endpoint}")
                        break
            except:
                continue
        
        return proyectos
    
    def _obtener_proyectos_en_evaluacion(self) -> List[Dict]:
        """Obtiene proyectos actualmente en evaluación"""
        proyectos = []
        
        urls = [
            f"{self.base_url}/proy_en_evaluacion/evaluacion.php",
            f"{self.base_url}/evaluacion/proyectos",
            f"{self.base_url}/busqueda/buscarProyecto.php?estado=evaluacion"
        ]
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Buscar tablas con proyectos
                    tablas = soup.find_all('table')
                    for tabla in tablas:
                        if self._es_tabla_proyectos(tabla):
                            proyectos_tabla = self._extraer_proyectos_de_tabla(tabla)
                            proyectos.extend(proyectos_tabla)
                    
                    # Buscar listas de proyectos
                    listas = soup.find_all(['ul', 'ol'], class_=re.compile('proyecto|lista'))
                    for lista in listas:
                        items = lista.find_all('li')
                        for item in items:
                            proyecto = self._extraer_proyecto_de_elemento(item)
                            if proyecto:
                                proyectos.append(proyecto)
                    
                    if proyectos:
                        logger.info(f"✅ {len(proyectos)} proyectos en evaluación desde {url}")
                        break
                        
            except Exception as e:
                logger.debug(f"Error obteniendo proyectos en evaluación: {e}")
                continue
        
        return proyectos
    
    def _obtener_proyectos_aprobados_recientes(self, dias_atras: int) -> List[Dict]:
        """Obtiene proyectos aprobados recientemente"""
        proyectos = []
        
        fecha_desde = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y%m%d')
        
        urls = [
            f"{self.base_url}/busqueda/buscarProyecto.php?estado=aprobado&fecha={fecha_desde}",
            f"{self.base_url}/aprobados/recientes",
            f"{self.base_url}/rca/ultimas"
        ]
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    proyectos_pagina = self._extraer_todos_proyectos(soup)
                    proyectos.extend(proyectos_pagina)
                    
                    if proyectos:
                        logger.info(f"✅ {len(proyectos)} proyectos aprobados desde {url}")
                        break
                        
            except Exception:
                continue
        
        return proyectos
    
    def _buscar_en_tabla_resultados(self, dias_atras: int) -> List[Dict]:
        """Busca proyectos en tabla de resultados con fechas específicas"""
        proyectos = []
        
        # Preparar búsqueda con fechas
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=dias_atras)
        
        # URLs de búsqueda con parámetros
        urls = [
            f"{self.base_url}/busqueda/buscarProyectoAction.php?_=1",
            f"{self.base_url}/busqueda/resultados.php",
            f"{self.base_url}/busqueda/proyectos"
        ]
        
        for url in urls:
            try:
                # Parámetros de búsqueda
                params = {
                    'fecha_desde': fecha_desde.strftime('%d/%m/%Y'),
                    'fecha_hasta': fecha_hasta.strftime('%d/%m/%Y'),
                    'tipo': '',  # Todos los tipos
                    'estado': '',  # Todos los estados
                    'buscar': '1'
                }
                
                response = self.session.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    proyectos_pagina = self._extraer_todos_proyectos(soup)
                    proyectos.extend(proyectos_pagina)
                    
                    if proyectos:
                        logger.info(f"✅ {len(proyectos)} proyectos desde búsqueda en {url}")
                        break
                        
            except Exception:
                continue
        
        return proyectos
    
    def _extraer_todos_proyectos(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae todos los proyectos de una página"""
        proyectos = []
        
        # Buscar en tablas
        tablas = soup.find_all('table')
        for tabla in tablas:
            if self._es_tabla_proyectos(tabla):
                proyectos_tabla = self._extraer_proyectos_de_tabla(tabla)
                proyectos.extend(proyectos_tabla)
        
        # Buscar en divs con clases específicas
        contenedores = soup.find_all('div', class_=re.compile('proyecto|resultado|item|card'))
        for contenedor in contenedores[:100]:
            proyecto = self._extraer_proyecto_de_elemento(contenedor)
            if proyecto:
                proyectos.append(proyecto)
        
        # Buscar en artículos
        articulos = soup.find_all('article')
        for articulo in articulos[:50]:
            proyecto = self._extraer_proyecto_de_elemento(articulo)
            if proyecto:
                proyectos.append(proyecto)
        
        return proyectos
    
    def _es_tabla_proyectos(self, tabla) -> bool:
        """Verifica si una tabla contiene proyectos"""
        try:
            # Verificar headers
            headers = tabla.find_all('th')
            header_text = ' '.join([h.get_text().lower() for h in headers])
            
            # Palabras clave que indican tabla de proyectos
            palabras_clave = ['proyecto', 'expediente', 'titular', 'tipo', 'fecha', 'estado', 'región']
            coincidencias = sum(1 for palabra in palabras_clave if palabra in header_text)
            
            # Si tiene al menos 3 palabras clave, es probable que sea tabla de proyectos
            if coincidencias >= 3:
                return True
            
            # Verificar cantidad de filas (más de 3 filas probablemente tiene contenido)
            filas = tabla.find_all('tr')
            if len(filas) > 3:
                # Verificar si tiene enlaces a expedientes
                enlaces = tabla.find_all('a', href=re.compile('expediente|proyecto'))
                if len(enlaces) > 0:
                    return True
            
            return False
            
        except:
            return False
    
    def _extraer_proyectos_de_tabla(self, tabla) -> List[Dict]:
        """Extrae proyectos de una tabla HTML"""
        proyectos = []
        
        try:
            filas = tabla.find_all('tr')
            
            # Detectar índices de columnas
            headers = tabla.find_all('th')
            indices = self._detectar_indices_columnas(headers)
            
            for fila in filas[1:]:  # Saltar header
                celdas = fila.find_all(['td', 'th'])
                
                if len(celdas) > 2:
                    proyecto = {}
                    
                    # Extraer información según índices detectados
                    for key, index in indices.items():
                        if index < len(celdas):
                            texto = celdas[index].get_text(strip=True)
                            if key == 'titulo':
                                # Buscar enlace en la celda
                                enlace = celdas[index].find('a')
                                if enlace:
                                    proyecto['titulo'] = enlace.get_text(strip=True)
                                    href = enlace.get('href', '')
                                    if href:
                                        proyecto['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                                else:
                                    proyecto['titulo'] = texto
                            else:
                                proyecto[key] = texto
                    
                    # Si no se detectaron índices, usar método genérico
                    if not indices:
                        proyecto = self._extraer_proyecto_generico(celdas)
                    
                    if proyecto and proyecto.get('titulo'):
                        proyectos.append(proyecto)
                        
        except Exception as e:
            logger.debug(f"Error extrayendo proyectos de tabla: {e}")
        
        return proyectos
    
    def _detectar_indices_columnas(self, headers) -> Dict[str, int]:
        """Detecta los índices de las columnas importantes"""
        indices = {}
        
        for i, header in enumerate(headers):
            texto = header.get_text(strip=True).lower()
            
            if any(palabra in texto for palabra in ['nombre', 'proyecto', 'título']):
                indices['titulo'] = i
            elif any(palabra in texto for palabra in ['tipo', 'presentación']):
                indices['tipo'] = i
            elif any(palabra in texto for palabra in ['fecha', 'ingreso', 'presentación']):
                indices['fecha_presentacion'] = i
            elif 'región' in texto:
                indices['region'] = i
            elif any(palabra in texto for palabra in ['estado', 'situación']):
                indices['estado'] = i
            elif any(palabra in texto for palabra in ['titular', 'empresa']):
                indices['titular'] = i
        
        return indices
    
    def _extraer_proyecto_generico(self, celdas) -> Dict:
        """Extrae proyecto de celdas sin índices específicos"""
        proyecto = {}
        
        for i, celda in enumerate(celdas):
            texto = celda.get_text(strip=True)
            
            # Primera celda con texto largo = título probable
            if i == 0 and len(texto) > 20:
                proyecto['titulo'] = texto
                # Buscar enlace
                enlace = celda.find('a')
                if enlace:
                    proyecto['titulo'] = enlace.get_text(strip=True)
                    href = enlace.get('href', '')
                    if href:
                        proyecto['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
            
            # Detectar tipo
            elif texto in ['DIA', 'EIA', 'Modificación DIA', 'Modificación EIA']:
                proyecto['tipo'] = texto
            
            # Detectar fecha
            elif re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', texto):
                proyecto['fecha_presentacion'] = texto.replace('-', '/')
            
            # Detectar región
            elif 'Región' in texto:
                proyecto['region'] = texto
            
            # Detectar estado
            elif any(estado in texto for estado in ['Calificación', 'Admisión', 'Aprobado', 'Evaluación']):
                proyecto['estado'] = texto
        
        return proyecto
    
    def _extraer_proyecto_de_elemento(self, elemento) -> Optional[Dict]:
        """Extrae información de proyecto de un elemento HTML genérico"""
        try:
            proyecto = {}
            texto = elemento.get_text(' ', strip=True)
            
            # Buscar título
            titulo_elem = elemento.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong'])
            if titulo_elem:
                proyecto['titulo'] = titulo_elem.get_text(strip=True)
            else:
                # Buscar en enlaces
                enlace = elemento.find('a')
                if enlace and len(enlace.get_text(strip=True)) > 20:
                    proyecto['titulo'] = enlace.get_text(strip=True)
                    href = enlace.get('href', '')
                    if href:
                        proyecto['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
            
            # Buscar fecha
            fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
            if fecha_match:
                proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
            
            # Buscar tipo
            if 'DIA' in texto:
                proyecto['tipo'] = 'DIA'
            elif 'EIA' in texto:
                proyecto['tipo'] = 'EIA'
            
            # Buscar región
            regiones = ['Arica', 'Tarapacá', 'Antofagasta', 'Atacama', 'Coquimbo',
                       'Valparaíso', 'Metropolitana', "O'Higgins", 'Maule', 'Ñuble',
                       'Biobío', 'Araucanía', 'Los Ríos', 'Los Lagos', 'Aysén', 'Magallanes']
            
            for region in regiones:
                if region in texto:
                    proyecto['region'] = f"Región de {region}"
                    break
            
            return proyecto if proyecto.get('titulo') else None
            
        except:
            return None
    
    def _convertir_json_a_proyecto(self, item: dict) -> Optional[Dict]:
        """Convierte un item JSON a formato de proyecto"""
        try:
            proyecto = {}
            
            # Mapear campos comunes
            campos_titulo = ['nombre', 'titulo', 'nombre_proyecto', 'project_name']
            for campo in campos_titulo:
                if campo in item:
                    proyecto['titulo'] = item[campo]
                    break
            
            campos_tipo = ['tipo', 'tipo_proyecto', 'type']
            for campo in campos_tipo:
                if campo in item:
                    proyecto['tipo'] = item[campo]
                    break
            
            campos_fecha = ['fecha', 'fecha_presentacion', 'fecha_ingreso', 'date']
            for campo in campos_fecha:
                if campo in item:
                    fecha = item[campo]
                    if isinstance(fecha, str):
                        proyecto['fecha_presentacion'] = fecha
                    break
            
            campos_region = ['region', 'region_nombre']
            for campo in campos_region:
                if campo in item:
                    proyecto['region'] = item[campo]
                    break
            
            return proyecto if proyecto.get('titulo') else None
            
        except:
            return None
    
    def _filtrar_proyectos_reales(self, proyectos: List[Dict]) -> List[Dict]:
        """Filtra solo proyectos reales, eliminando noticias y otros contenidos"""
        proyectos_filtrados = []
        
        # Palabras que indican que NO es un proyecto
        palabras_excluir = [
            'realiza observaciones',
            'desarrolla proceso',
            'guías',
            'instructivos',
            'criterios',
            'noticias',
            'aviso',
            'comunicado',
            'invitación'
        ]
        
        for proyecto in proyectos:
            titulo = proyecto.get('titulo', '').lower()
            
            # Verificar que no contenga palabras excluidas
            es_noticia = any(palabra in titulo for palabra in palabras_excluir)
            
            # Verificar que tenga estructura de proyecto real
            tiene_tipo = proyecto.get('tipo') in ['DIA', 'EIA', 'Modificación DIA', 'Modificación EIA']
            tiene_fecha = bool(proyecto.get('fecha_presentacion'))
            titulo_valido = len(titulo) > 10 and not titulo.startswith('sea ')
            
            # Un proyecto real debe tener título válido y preferiblemente tipo o fecha
            if not es_noticia and titulo_valido and (tiene_tipo or tiene_fecha or 'proyecto' in titulo):
                proyectos_filtrados.append(proyecto)
        
        return proyectos_filtrados