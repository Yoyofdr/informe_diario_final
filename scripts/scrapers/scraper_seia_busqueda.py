"""
Scraper para la página de búsqueda de proyectos del SEIA
https://seia.sea.gob.cl/busqueda/buscarProyectoResumen.php
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import re
import time

logger = logging.getLogger(__name__)

class ScraperSEIABusqueda:
    def __init__(self):
        """
        Inicializa el scraper para la búsqueda del SEIA
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
        self.base_url = "https://seia.sea.gob.cl"
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoResumen.php"
        self.ajax_url = f"{self.base_url}/busqueda/buscarProyectoResumenAction.php"
        
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos del SEIA mediante búsqueda AJAX
        """
        proyectos = []
        fecha_limite = datetime.now() - timedelta(days=365)  # Solo proyectos del último año
        
        try:
            logger.info(f"🔍 Buscando proyectos SEIA recientes...")
            
            # Primero obtener la página para capturar cookies
            response = self.session.get(self.search_url)
            if response.status_code != 200:
                logger.error(f"Error al acceder a la página: {response.status_code}")
                return []
            
            # Usar el endpoint AJAX para obtener datos
            proyectos = self._obtener_proyectos_ajax()
            
            # Filtrar proyectos antiguos
            proyectos_recientes = []
            for p in proyectos:
                fecha_str = p.get('fecha')
                if fecha_str:
                    try:
                        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
                        if fecha >= fecha_limite:
                            proyectos_recientes.append(p)
                        else:
                            logger.debug(f"Filtrando proyecto antiguo: {p.get('titulo', '')} ({fecha_str})")
                    except:
                        pass
            
            # Si no hay proyectos recientes, retornar lista vacía
            if not proyectos_recientes:
                logger.warning("No se encontraron proyectos recientes del SEA")
                proyectos_recientes = []
            
            # Eliminar duplicados por título
            proyectos_unicos = []
            titulos_vistos = set()
            for p in proyectos_recientes:
                titulo = p.get('titulo', '')
                if titulo and titulo not in titulos_vistos:
                    titulos_vistos.add(titulo)
                    proyectos_unicos.append(p)
            
            logger.info(f"✅ Total proyectos recientes encontrados: {len(proyectos_unicos)}")
            return proyectos_unicos[:20]  # Limitar a 20 proyectos
            
        except Exception as e:
            logger.error(f"❌ Error en scraper SEIA: {str(e)}")
            return []
    
    def _obtener_proyectos_ajax(self) -> List[Dict]:
        """
        Obtiene proyectos usando el endpoint AJAX del SEIA
        """
        proyectos = []
        
        try:
            # Headers específicos para AJAX
            ajax_headers = self.session.headers.copy()
            ajax_headers.update({
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': self.search_url
            })
            
            # Parámetros para obtener proyectos (DataTables)
            params = {
                'draw': '1',
                'start': '0',
                'length': '100',  # Obtener hasta 100 proyectos
                'order[0][column]': '13',  # Ordenar por fecha
                'order[0][dir]': 'desc'    # Más recientes primero
            }
            
            response = self.session.get(
                self.ajax_url,
                params=params,
                headers=ajax_headers,
                timeout=15
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if 'data' in data and data['data']:
                        logger.info(f"✅ Encontrados {len(data['data'])} proyectos via AJAX")
                        
                        for item in data['data']:
                            proyecto = self._convertir_proyecto_ajax(item)
                            if proyecto:
                                proyectos.append(proyecto)
                    else:
                        logger.warning("No se encontraron proyectos en la respuesta AJAX")
                        
                except Exception as e:
                    logger.error(f"Error parseando JSON: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error en petición AJAX: {str(e)}")
        
        return proyectos
    
    def _convertir_proyecto_ajax(self, item: dict) -> Optional[Dict]:
        """
        Convierte un proyecto del formato AJAX al formato del informe
        """
        try:
            # Convertir timestamp a fecha
            fecha_timestamp = item.get('FECHA_PRESENTACION', '')
            if fecha_timestamp and str(fecha_timestamp).isdigit():
                fecha = datetime.fromtimestamp(int(fecha_timestamp)).strftime('%d/%m/%Y')
            else:
                # Buscar fecha en formato string
                fecha_str = item.get('FECHA_PRESENTACION_FORMAT') or item.get('FECHA_PRESENTACION_STR') or item.get('FECHA')
                if fecha_str:
                    fecha = fecha_str
                else:
                    # Si no hay fecha, no incluir el proyecto (no usar fecha actual)
                    return None
            
            # Determinar tipo basado en estado
            estado = item.get('ESTADO_PROYECTO', '').lower()
            if 'aprob' in estado:
                tipo = 'RCA Aprobada'
                relevancia = 7.0
            elif 'rechaz' in estado:
                tipo = 'RCA Rechazada'
                relevancia = 8.0
            elif 'calific' in estado:
                tipo = 'En Calificación'
                relevancia = 6.0
            else:
                tipo = item.get('WORKFLOW_DESCRIPCION', 'Proyecto SEIA')
                relevancia = 5.0
            
            # Formatear inversión
            inversion_str = item.get('INVERSION_MM_FORMAT', '')
            inversion_mmusd = 0
            if inversion_str:
                try:
                    # Remover comas y convertir
                    inversion_mmusd = float(inversion_str.replace(',', '.'))
                except:
                    pass
            
            # Agregar "Proyecto" al título si no lo tiene
            titulo_original = item.get('EXPEDIENTE_NOMBRE', 'Sin nombre')
            if not titulo_original.lower().startswith('proyecto'):
                titulo = f"Proyecto {titulo_original}"
            else:
                titulo = titulo_original
            
            proyecto = {
                'fuente': 'SEA',
                'tipo': tipo,
                'titulo': titulo,
                'empresa': item.get('TITULAR', ''),
                'fecha': fecha,
                'region': item.get('REGION_NOMBRE', ''),
                'comuna': item.get('COMUNA_NOMBRE', ''),
                'estado': item.get('ESTADO_PROYECTO', ''),
                'tipo_proyecto': item.get('DESCRIPCION_TIPOLOGIA', ''),
                'inversion_mmusd': inversion_mmusd,
                'expediente_id': item.get('EXPEDIENTE_ID', ''),
                'url': item.get('EXPEDIENTE_URL_FICHA', item.get('EXPEDIENTE_URL_PPAL', self.search_url)),
                'relevancia': relevancia
            }
            
            # Generar resumen
            partes = []
            
            partes.append(f"{tipo} - {proyecto['estado']}")
            
            if proyecto['empresa']:
                partes.append(f"Titular: {proyecto['empresa']}")
            
            if proyecto['region']:
                partes.append(f"Ubicación: {proyecto['region']}")
                if proyecto['comuna']:
                    partes.append(proyecto['comuna'])
            
            if inversion_mmusd > 0:
                partes.append(f"Inversión: USD {inversion_mmusd:.1f} millones")
            
            if proyecto['tipo_proyecto']:
                partes.append(f"Tipo: {proyecto['tipo_proyecto']}")
            
            proyecto['resumen'] = '. '.join(partes)
            
            return proyecto
            
        except Exception as e:
            logger.debug(f"Error convirtiendo proyecto: {str(e)}")
            return None
    
    def _realizar_busqueda(self, parametros: dict) -> List[Dict]:
        """
        Realiza una búsqueda específica con parámetros
        """
        try:
            # Parámetros base de búsqueda
            data = {
                'tipo_proy': '0',  # Todos los tipos
                'estado': '0',     # Todos los estados
                'region': '0',     # Todas las regiones
                'buscar': 'Buscar',
                'cantidad_por_pagina': '50'
            }
            
            # Agregar parámetros específicos
            data.update(parametros)
            
            logger.debug(f"Realizando búsqueda con parámetros: {parametros}")
            
            # Realizar POST para búsqueda
            response = self.session.post(
                self.search_url,
                data=data,
                timeout=15,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                logger.warning(f"Respuesta no exitosa: {response.status_code}")
                return []
            
            # Parsear resultados
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tabla de resultados
            tablas = soup.find_all('table', class_=['table', 'tabla-datos', 'listado'])
            
            if not tablas:
                # Buscar cualquier tabla
                tablas = soup.find_all('table')
            
            proyectos = []
            
            for tabla in tablas:
                # Buscar filas con datos
                filas = tabla.find_all('tr')
                
                for fila in filas[1:]:  # Saltar header
                    celdas = fila.find_all(['td', 'th'])
                    
                    if len(celdas) >= 3:  # Mínimo 3 columnas
                        proyecto = self._extraer_proyecto_de_fila(celdas, soup)
                        if proyecto:
                            proyectos.append(proyecto)
            
            # Si no hay tablas, buscar divs con proyectos
            if not proyectos:
                proyectos = self._buscar_proyectos_en_divs(soup)
            
            logger.info(f"📊 Encontrados {len(proyectos)} proyectos en esta búsqueda")
            return proyectos
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            return []
    
    def _extraer_proyecto_de_fila(self, celdas: list, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Extrae información de proyecto desde una fila de tabla
        """
        try:
            # Extraer texto de todas las celdas
            textos = [c.get_text(strip=True) for c in celdas]
            
            # Filtrar celdas vacías
            textos = [t for t in textos if t and len(t) > 2]
            
            if not textos:
                return None
            
            proyecto = {
                'fuente': 'SEA',
                'fecha': None  # Se establecerá después
            }
            
            # Buscar enlace al proyecto
            enlace = None
            for celda in celdas:
                link = celda.find('a', href=True)
                if link:
                    enlace = link['href']
                    if not enlace.startswith('http'):
                        enlace = self.base_url + enlace
                    proyecto['url'] = enlace
                    break
            
            # Intentar identificar campos por posición o contenido
            for i, texto in enumerate(textos):
                texto_lower = texto.lower()
                
                # Identificar tipo de campo
                if i == 0 or 'proyecto' in texto_lower or len(texto) > 30:
                    proyecto['titulo'] = texto[:200]
                elif 'eia' in texto_lower or 'dia' in texto_lower:
                    proyecto['tipo_documento'] = texto
                elif any(region in texto_lower for region in ['región', 'metropolitana', 'antofagasta', 'valparaíso']):
                    proyecto['region'] = texto
                elif re.match(r'\d{2}/\d{2}/\d{4}', texto):
                    proyecto['fecha'] = texto
                elif 'aprob' in texto_lower:
                    proyecto['estado'] = 'Aprobado'
                    proyecto['tipo'] = 'RCA Aprobada'
                elif 'rechaz' in texto_lower:
                    proyecto['estado'] = 'Rechazado'
                    proyecto['tipo'] = 'RCA Rechazada'
                elif 'calific' in texto_lower:
                    proyecto['estado'] = 'En Calificación'
                    proyecto['tipo'] = 'En Evaluación'
                elif any(estado in texto_lower for estado in ['admitid', 'desist', 'términ']):
                    proyecto['estado'] = texto
                    proyecto['tipo'] = 'Estado: ' + texto
            
            # Valores por defecto
            if 'titulo' not in proyecto:
                proyecto['titulo'] = ' - '.join(textos[:2])
            
            if 'tipo' not in proyecto:
                proyecto['tipo'] = 'Proyecto en SEIA'
            
            # Si no hay fecha, no incluir el proyecto
            if not proyecto.get('fecha') or proyecto['fecha'] is None:
                return None
            
            # Generar resumen
            proyecto['resumen'] = self._generar_resumen(proyecto, textos)
            
            # Calcular relevancia
            proyecto['relevancia'] = self._calcular_relevancia(proyecto)
            
            # URL por defecto
            if 'url' not in proyecto:
                proyecto['url'] = self.search_url
            
            return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de fila: {str(e)}")
            return None
    
    def _buscar_proyectos_en_divs(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Busca proyectos en divs cuando no hay tablas
        """
        proyectos = []
        
        try:
            # Buscar contenedores de proyectos
            contenedores = soup.find_all(['div', 'article'], 
                                        class_=re.compile('proyecto|project|item|resultado', re.I))
            
            for contenedor in contenedores[:30]:
                texto = contenedor.get_text(strip=True)
                
                if len(texto) < 20:
                    continue
                
                proyecto = {
                    'fuente': 'SEA',
                    'fecha': None,  # Sin fecha, se filtrará después
                    'tipo': 'Proyecto en SEIA'
                }
                
                # Buscar título
                titulo = contenedor.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if titulo:
                    proyecto['titulo'] = titulo.get_text(strip=True)[:200]
                else:
                    proyecto['titulo'] = texto[:100]
                
                # Buscar enlace
                link = contenedor.find('a', href=True)
                if link:
                    url = link['href']
                    if not url.startswith('http'):
                        url = self.base_url + url
                    proyecto['url'] = url
                else:
                    proyecto['url'] = self.search_url
                
                # Buscar estado
                if 'aprob' in texto.lower():
                    proyecto['tipo'] = 'RCA Aprobada'
                    proyecto['relevancia'] = 7.0
                elif 'rechaz' in texto.lower():
                    proyecto['tipo'] = 'RCA Rechazada'
                    proyecto['relevancia'] = 8.0
                else:
                    proyecto['relevancia'] = 5.0
                
                # Generar resumen
                proyecto['resumen'] = texto[:300]
                
                proyectos.append(proyecto)
                
        except Exception as e:
            logger.debug(f"Error buscando en divs: {str(e)}")
        
        return proyectos
    
    def _obtener_proyectos_principales(self) -> List[Dict]:
        """
        Obtiene proyectos de la página principal sin búsqueda
        """
        try:
            response = self.session.get(self.search_url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar proyectos destacados o recientes
            proyectos = []
            
            # Buscar enlaces a expedientes
            enlaces = soup.find_all('a', href=re.compile(r'expediente|ficha|proyecto', re.I))
            
            for enlace in enlaces[:20]:
                texto = enlace.get_text(strip=True)
                
                if len(texto) < 10:
                    continue
                
                # Sin fecha conocida, no incluir estos proyectos
                continue  # Saltar proyectos sin fecha
                
                proyectos.append(proyecto)
            
            return proyectos
            
        except Exception as e:
            logger.error(f"Error obteniendo proyectos principales: {str(e)}")
            return []
    
    def _generar_resumen(self, proyecto: dict, textos: list) -> str:
        """
        Genera un resumen del proyecto
        """
        partes = []
        
        # Tipo y estado
        if 'estado' in proyecto:
            partes.append(f"Estado: {proyecto['estado']}")
        
        if 'tipo_documento' in proyecto:
            partes.append(f"Tipo: {proyecto['tipo_documento']}")
        
        if 'region' in proyecto:
            partes.append(f"Región: {proyecto['region']}")
        
        if 'fecha' in proyecto and proyecto['fecha'] != datetime.now().strftime('%d/%m/%Y'):
            partes.append(f"Fecha: {proyecto['fecha']}")
        
        # Agregar información adicional de los textos
        info_adicional = ' | '.join(textos[2:5]) if len(textos) > 2 else ''
        if info_adicional and len(info_adicional) > 10:
            partes.append(info_adicional[:200])
        
        resumen = '. '.join(partes)
        
        # Si el resumen es muy corto, usar el título
        if len(resumen) < 30:
            resumen = proyecto.get('titulo', 'Proyecto en evaluación ambiental')
        
        return resumen
    
    def _calcular_relevancia(self, proyecto: dict) -> float:
        """
        Calcula la relevancia del proyecto
        """
        relevancia = 5.0
        
        # Por estado
        estado = proyecto.get('estado', '').lower()
        tipo = proyecto.get('tipo', '').lower()
        
        if 'aprob' in estado or 'aprob' in tipo:
            relevancia = 7.0
        elif 'rechaz' in estado or 'rechaz' in tipo:
            relevancia = 8.0
        elif 'calific' in estado or 'calific' in tipo:
            relevancia = 6.0
        
        # Por tipo de documento
        tipo_doc = proyecto.get('tipo_documento', '').upper()
        if 'EIA' in tipo_doc:
            relevancia += 1.0  # Estudios de Impacto Ambiental son más relevantes
        
        # Por región (proyectos en ciertas regiones pueden ser más relevantes)
        region = proyecto.get('region', '').lower()
        if any(r in region for r in ['metropolitana', 'valparaíso', 'biobío']):
            relevancia += 0.5
        
        return min(relevancia, 10.0)
    
    # Método eliminado - no usar datos de ejemplo