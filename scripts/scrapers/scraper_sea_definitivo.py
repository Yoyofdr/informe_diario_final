#!/usr/bin/env python3
"""
Scraper SEA DEFINITIVO - Solución completa para obtener proyectos del SEIA
Usa búsqueda por POST en buscarProyectoResumen.php
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import re
import time

logger = logging.getLogger(__name__)

class ScraperSEADefinitivo:
    def __init__(self):
        """Inicializa el scraper definitivo del SEIA"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
        self.base_url = "https://seia.sea.gob.cl"
        self.search_page = f"{self.base_url}/busqueda/buscarProyecto.php"
        self.search_action = f"{self.base_url}/busqueda/buscarProyectoResumen.php"
        
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos recientes del SEIA usando búsqueda POST
        
        Args:
            dias_atras: Número de días hacia atrás para buscar proyectos
            
        Returns:
            Lista de diccionarios con información de proyectos
        """
        proyectos = []
        
        try:
            logger.info(f"🌊 Iniciando scraper SEA definitivo (últimos {dias_atras} días)...")
            
            # Paso 1: Obtener la página de búsqueda para establecer cookies
            logger.info("📋 Obteniendo página de búsqueda...")
            response = self.session.get(self.search_page, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error al acceder a la página: {response.status_code}")
                return []
            
            # Extraer token CSRF si existe
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = None
            token_input = soup.find('input', {'name': 'csrf_token'}) or \
                         soup.find('input', {'name': '_token'}) or \
                         soup.find('input', {'name': 'authenticity_token'})
            
            if token_input:
                csrf_token = token_input.get('value')
                logger.info("🔐 Token CSRF obtenido")
            
            # Paso 2: Realizar búsqueda con fechas específicas
            fecha_hasta = datetime.now()
            fecha_desde = fecha_hasta - timedelta(days=dias_atras)
            
            # Datos del formulario
            form_data = {
                'nombre_proyecto': '',
                'titular': '',
                'fecha_desde': fecha_desde.strftime('%d/%m/%Y'),
                'fecha_hasta': fecha_hasta.strftime('%d/%m/%Y'),
                'region': '',
                'tipoproyecto': '',
                'comuna': '',
                'sector': '',
                'subsector': '',
                'estado': '',
                'buscar': 'Buscar',
                'submit': 'buscar'
            }
            
            if csrf_token:
                form_data['csrf_token'] = csrf_token
            
            logger.info(f"🔍 Buscando proyectos del {form_data['fecha_desde']} al {form_data['fecha_hasta']}")
            
            # Headers específicos para POST
            post_headers = self.session.headers.copy()
            post_headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.search_page,
                'Origin': self.base_url
            })
            
            # Realizar búsqueda POST
            response = self.session.post(
                self.search_action,
                data=form_data,
                headers=post_headers,
                timeout=20,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                logger.error(f"Error en búsqueda POST: {response.status_code}")
                return []
            
            # Paso 3: Parsear resultados
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tabla de resultados (puede tener diferentes IDs/clases)
            tabla = soup.find('table', {'id': 'tabla-resultado'}) or \
                   soup.find('table', {'class': 'resultado'}) or \
                   soup.find('table', {'class': 'table'}) or \
                   soup.find('table')
            
            if tabla:
                filas = tabla.find_all('tr')
                logger.info(f"📊 Tabla encontrada con {len(filas)} filas")
                
                # Procesar cada fila
                for i, fila in enumerate(filas[1:], 1):  # Saltar header
                    if i > 100:  # Limitar a 100 proyectos
                        break
                    
                    proyecto = self._extraer_proyecto_de_fila(fila)
                    if proyecto:
                        # Verificar que sea reciente
                        if self._es_proyecto_reciente(proyecto, dias_atras):
                            proyectos.append(proyecto)
                            logger.debug(f"✅ Proyecto: {proyecto.get('titulo', '')[:50]}...")
            else:
                # Si no hay tabla, buscar en divs o elementos individuales
                logger.info("🔍 Buscando proyectos en elementos individuales...")
                
                # Buscar por diferentes selectores
                elementos = soup.find_all('div', class_=re.compile('proyecto|resultado|item')) + \
                           soup.find_all('article') + \
                           soup.find_all('li', class_=re.compile('proyecto|resultado'))
                
                for elemento in elementos[:100]:
                    proyecto = self._extraer_proyecto_de_elemento(elemento)
                    if proyecto and self._es_proyecto_reciente(proyecto, dias_atras):
                        proyectos.append(proyecto)
            
            # Si aún no hay proyectos, buscar en el texto completo
            if not proyectos:
                logger.info("🔍 Analizando texto completo de la página...")
                proyectos = self._extraer_proyectos_del_texto(response.text, dias_atras)
            
            logger.info(f"✅ Total proyectos encontrados: {len(proyectos)}")
            
        except Exception as e:
            logger.error(f"❌ Error en scraper SEA definitivo: {str(e)}")
        
        return proyectos[:50]  # Limitar a 50 proyectos máximo
    
    def _extraer_proyecto_de_fila(self, fila) -> Optional[Dict]:
        """Extrae información de un proyecto desde una fila de tabla"""
        try:
            celdas = fila.find_all(['td', 'th'])
            
            if len(celdas) < 2:
                return None
            
            proyecto = {}
            
            # Analizar cada celda
            for i, celda in enumerate(celdas):
                texto = celda.get_text(strip=True)
                
                # Buscar título/nombre (generalmente primera celda con texto largo)
                if i == 0 or (len(texto) > 20 and not proyecto.get('titulo')):
                    # Buscar enlace dentro de la celda
                    enlace = celda.find('a')
                    if enlace:
                        proyecto['titulo'] = enlace.get_text(strip=True)
                        href = enlace.get('href', '')
                        if href:
                            proyecto['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                    elif texto and len(texto) > 10:
                        proyecto['titulo'] = texto
                
                # Detectar tipo de proyecto
                if texto in ['DIA', 'EIA', 'Modificación DIA', 'Modificación EIA']:
                    proyecto['tipo'] = texto
                
                # Detectar fecha (formato DD/MM/YYYY o DD-MM-YYYY)
                fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
                if fecha_match and not proyecto.get('fecha_presentacion'):
                    proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
                
                # Detectar región
                if 'Región' in texto or any(r in texto for r in ['Metropolitana', 'Valparaíso', 'Biobío', 'Maule']):
                    proyecto['region'] = texto
                
                # Detectar estado
                estados = ['En Calificación', 'En Admisión', 'Aprobado', 'Rechazado', 'En Evaluación']
                for estado in estados:
                    if estado.lower() in texto.lower():
                        proyecto['estado'] = estado
                        break
                
                # Detectar titular/empresa
                if i > 0 and len(texto) > 5 and not any(x in texto for x in ['Región', 'DIA', 'EIA', '/']):
                    if not proyecto.get('titular'):
                        proyecto['titular'] = texto
            
            # Validar proyecto mínimo
            if proyecto.get('titulo'):
                # Si no tiene fecha, intentar extraerla del título o URL
                if not proyecto.get('fecha_presentacion'):
                    fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', str(proyecto))
                    if fecha_match:
                        proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
                
                return proyecto
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de fila: {e}")
            return None
    
    def _extraer_proyecto_de_elemento(self, elemento) -> Optional[Dict]:
        """Extrae información de un proyecto desde un elemento HTML genérico"""
        try:
            proyecto = {}
            texto_completo = elemento.get_text(' ', strip=True)
            
            # Buscar título en headers o enlaces
            titulo_elem = elemento.find(['h1', 'h2', 'h3', 'h4', 'h5', 'a'])
            if titulo_elem:
                proyecto['titulo'] = titulo_elem.get_text(strip=True)
                if titulo_elem.name == 'a':
                    href = titulo_elem.get('href', '')
                    if href:
                        proyecto['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
            
            # Buscar fecha
            fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto_completo)
            if fecha_match:
                proyecto['fecha_presentacion'] = fecha_match.group(1).replace('-', '/')
            
            # Buscar tipo
            if 'DIA' in texto_completo:
                proyecto['tipo'] = 'DIA'
            elif 'EIA' in texto_completo:
                proyecto['tipo'] = 'EIA'
            
            # Buscar región
            regiones = ['Arica', 'Tarapacá', 'Antofagasta', 'Atacama', 'Coquimbo', 
                       'Valparaíso', 'Metropolitana', 'O\'Higgins', 'Maule', 'Biobío',
                       'Araucanía', 'Los Ríos', 'Los Lagos', 'Aysén', 'Magallanes']
            for region in regiones:
                if region in texto_completo:
                    proyecto['region'] = f"Región {region}" if not texto_completo.startswith('Región') else region
                    break
            
            return proyecto if proyecto.get('titulo') else None
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de elemento: {e}")
            return None
    
    def _extraer_proyectos_del_texto(self, html_text: str, dias_atras: int) -> List[Dict]:
        """Extrae proyectos directamente del texto HTML usando expresiones regulares"""
        proyectos = []
        
        try:
            # Buscar patrones de proyectos en el HTML
            # Patrón: nombre del proyecto + tipo + fecha
            patron = r'([^<>\n]{20,150})\s*</[^>]+>\s*<[^>]+>\s*(DIA|EIA)[^<]*</[^>]+>\s*<[^>]+>\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})'
            
            matches = re.findall(patron, html_text, re.IGNORECASE)
            
            for match in matches:
                titulo, tipo, fecha = match
                titulo = titulo.strip()
                fecha = fecha.replace('-', '/')
                
                proyecto = {
                    'titulo': titulo,
                    'tipo': tipo.upper(),
                    'fecha_presentacion': fecha
                }
                
                # Verificar que sea reciente
                if self._es_proyecto_reciente(proyecto, dias_atras):
                    proyectos.append(proyecto)
                    logger.debug(f"✅ Proyecto extraído del texto: {titulo[:50]}...")
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyectos del texto: {e}")
        
        return proyectos
    
    def _es_proyecto_reciente(self, proyecto: Dict, dias_atras: int) -> bool:
        """Verifica si un proyecto es de los últimos días"""
        try:
            fecha_str = proyecto.get('fecha_presentacion', '')
            if not fecha_str:
                return False
            
            # Normalizar formato de fecha
            fecha_str = fecha_str.replace('-', '/')
            
            # Parsear fecha
            for formato in ['%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d']:
                try:
                    fecha = datetime.strptime(fecha_str, formato)
                    diferencia = datetime.now() - fecha
                    
                    # Verificar que no sea del futuro ni muy antiguo
                    if diferencia.days <= dias_atras and diferencia.days >= -1:
                        return True
                    break
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error verificando fecha: {e}")
            return False