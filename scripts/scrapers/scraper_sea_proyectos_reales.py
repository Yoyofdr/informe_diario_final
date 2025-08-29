#!/usr/bin/env python3
"""
Scraper SEA para obtener PROYECTOS REALES (no noticias)
Busca específicamente en la sección de proyectos en evaluación del SEIA
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class ScraperSEAProyectosReales:
    def __init__(self):
        """Inicializa el scraper con URLs específicas de proyectos"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'es-ES,es;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://seia.sea.gob.cl/'
        })
        
        # URLs específicas para proyectos reales
        self.urls_proyectos = {
            # Proyectos en evaluación (los más recientes)
            'evaluacion': 'https://seia.sea.gob.cl/busqueda/buscarProyectoAction.php',
            
            # Proyectos con RCA (aprobados recientemente)
            'rca': 'https://seia.sea.gob.cl/busqueda/buscarProyectoAction.php',
            
            # API de búsqueda general
            'busqueda': 'https://seia.sea.gob.cl/busqueda/buscarProyectoAction.php'
        }
    
    def obtener_datos_sea(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos REALES del SEA de los últimos días
        """
        logger.info(f"🎯 Buscando PROYECTOS REALES del SEA (últimos {dias_atras} días)")
        
        proyectos_totales = []
        proyectos_ids = set()  # Para evitar duplicados
        
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=dias_atras)
        
        # Estrategia 1: Buscar proyectos en evaluación
        proyectos_evaluacion = self._buscar_proyectos_evaluacion(fecha_desde, fecha_hasta)
        for p in proyectos_evaluacion:
            if p.get('id') not in proyectos_ids:
                proyectos_totales.append(p)
                proyectos_ids.add(p.get('id'))
        
        # Estrategia 2: Buscar proyectos con RCA reciente
        proyectos_rca = self._buscar_proyectos_con_rca(fecha_desde, fecha_hasta)
        for p in proyectos_rca:
            if p.get('id') not in proyectos_ids:
                proyectos_totales.append(p)
                proyectos_ids.add(p.get('id'))
        
        # Estrategia 3: Buscar por término específico (DIA/EIA)
        proyectos_busqueda = self._buscar_proyectos_por_tipo(fecha_desde, fecha_hasta)
        for p in proyectos_busqueda:
            if p.get('id') not in proyectos_ids:
                proyectos_totales.append(p)
                proyectos_ids.add(p.get('id'))
        
        # Filtrar solo proyectos reales
        proyectos_reales = self._filtrar_proyectos_reales(proyectos_totales)
        
        logger.info(f"✅ Total proyectos REALES encontrados: {len(proyectos_reales)}")
        
        # Log de proyectos específicos del 26/08
        self._verificar_proyectos_26_agosto(proyectos_reales)
        
        return proyectos_reales
    
    def _buscar_proyectos_evaluacion(self, fecha_desde: datetime, fecha_hasta: datetime) -> List[Dict]:
        """Busca proyectos actualmente en evaluación"""
        proyectos = []
        
        try:
            # Parámetros específicos para proyectos en evaluación
            params = {
                'tipo': 'evaluacion',
                'estado': 'en_calificacion',
                'fecha_desde': fecha_desde.strftime('%Y-%m-%d'),
                'fecha_hasta': fecha_hasta.strftime('%Y-%m-%d'),
                '_': str(int(datetime.now().timestamp() * 1000))
            }
            
            logger.info("🔍 Buscando proyectos EN EVALUACIÓN...")
            response = self.session.get(
                self.urls_proyectos['evaluacion'],
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                # Intentar parsear como JSON
                try:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            proyecto = self._procesar_proyecto_json(item)
                            if proyecto:
                                proyectos.append(proyecto)
                except:
                    # Si no es JSON, parsear HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    proyectos.extend(self._extraer_proyectos_html(soup))
            
            logger.info(f"   Encontrados: {len(proyectos)} en evaluación")
            
        except Exception as e:
            logger.error(f"Error buscando proyectos en evaluación: {e}")
        
        return proyectos
    
    def _buscar_proyectos_con_rca(self, fecha_desde: datetime, fecha_hasta: datetime) -> List[Dict]:
        """Busca proyectos con RCA (aprobados) reciente"""
        proyectos = []
        
        try:
            # Parámetros para proyectos con RCA
            params = {
                'tipo': 'rca',
                'estado': 'aprobado',
                'fecha_desde': fecha_desde.strftime('%Y-%m-%d'),
                'fecha_hasta': fecha_hasta.strftime('%Y-%m-%d'),
                '_': str(int(datetime.now().timestamp() * 1000))
            }
            
            logger.info("🔍 Buscando proyectos con RCA RECIENTE...")
            response = self.session.get(
                self.urls_proyectos['rca'],
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            proyecto = self._procesar_proyecto_json(item)
                            if proyecto:
                                proyectos.append(proyecto)
                except:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    proyectos.extend(self._extraer_proyectos_html(soup))
            
            logger.info(f"   Encontrados: {len(proyectos)} con RCA")
            
        except Exception as e:
            logger.error(f"Error buscando proyectos con RCA: {e}")
        
        return proyectos
    
    def _buscar_proyectos_por_tipo(self, fecha_desde: datetime, fecha_hasta: datetime) -> List[Dict]:
        """Busca proyectos por tipo (DIA/EIA)"""
        proyectos = []
        
        tipos = ['DIA', 'EIA']
        
        for tipo in tipos:
            try:
                params = {
                    'nombre': '',  # Buscar todos
                    'tipo_proyecto': tipo,
                    'fecha_desde': fecha_desde.strftime('%Y-%m-%d'),
                    'fecha_hasta': fecha_hasta.strftime('%Y-%m-%d'),
                    '_': str(int(datetime.now().timestamp() * 1000))
                }
                
                logger.info(f"🔍 Buscando proyectos tipo {tipo}...")
                response = self.session.get(
                    self.urls_proyectos['busqueda'],
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            for item in data:
                                proyecto = self._procesar_proyecto_json(item)
                                if proyecto:
                                    proyecto['tipo'] = tipo
                                    proyectos.append(proyecto)
                    except:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        for p in self._extraer_proyectos_html(soup):
                            p['tipo'] = tipo
                            proyectos.append(p)
                
                logger.info(f"   Encontrados: {len(proyectos)} tipo {tipo}")
                
            except Exception as e:
                logger.error(f"Error buscando proyectos tipo {tipo}: {e}")
        
        return proyectos
    
    def _procesar_proyecto_json(self, item: dict) -> Optional[Dict]:
        """Procesa un proyecto desde JSON"""
        try:
            # Mapear campos del JSON a nuestro formato
            proyecto = {
                'id': item.get('id', item.get('codigo', '')),
                'titulo': item.get('nombre', item.get('titulo', '')),
                'tipo': item.get('tipo', 'DIA'),
                'empresa': item.get('titular', item.get('empresa', '')),
                'region': item.get('region', ''),
                'comuna': item.get('comuna', ''),
                'estado': item.get('estado', 'En evaluación'),
                'fecha_presentacion': item.get('fecha_presentacion', 
                                             item.get('fecha', datetime.now().strftime('%Y-%m-%d'))),
                'inversion_mmusd': float(item.get('inversion', 0)) / 1000000 if item.get('inversion') else 0,
                'fuente': 'SEA',
                'url': f"https://seia.sea.gob.cl/expediente/expedientesEvaluacion.php?id={item.get('id', '')}"
            }
            
            # Generar resumen
            proyecto['resumen'] = self._generar_resumen_proyecto(proyecto)
            
            # Calcular relevancia
            proyecto['relevancia'] = self._calcular_relevancia(proyecto)
            
            return proyecto if proyecto['titulo'] else None
            
        except Exception as e:
            logger.debug(f"Error procesando proyecto JSON: {e}")
            return None
    
    def _extraer_proyectos_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae proyectos desde HTML"""
        proyectos = []
        
        # Buscar tablas con proyectos
        tablas = soup.find_all('table')
        
        for tabla in tablas:
            filas = tabla.find_all('tr')[1:]  # Saltar header
            
            for fila in filas:
                proyecto = self._extraer_proyecto_de_fila(fila)
                if proyecto:
                    proyectos.append(proyecto)
        
        # También buscar divs con clase proyecto
        divs_proyecto = soup.find_all('div', class_=re.compile('proyecto|item|resultado'))
        
        for div in divs_proyecto:
            proyecto = self._extraer_proyecto_de_div(div)
            if proyecto:
                proyectos.append(proyecto)
        
        return proyectos
    
    def _extraer_proyecto_de_fila(self, fila) -> Optional[Dict]:
        """Extrae un proyecto desde una fila de tabla"""
        try:
            celdas = fila.find_all('td')
            if len(celdas) < 2:
                return None
            
            proyecto = {}
            
            # Buscar información en las celdas
            for i, celda in enumerate(celdas):
                texto = celda.get_text(strip=True)
                
                # Primera celda suele ser el nombre
                if i == 0 and len(texto) > 10:
                    proyecto['titulo'] = texto
                    # Buscar enlace
                    enlace = celda.find('a')
                    if enlace and enlace.get('href'):
                        proyecto['url'] = f"https://seia.sea.gob.cl{enlace['href']}"
                        # Extraer ID del enlace
                        id_match = re.search(r'id=(\d+)', enlace['href'])
                        if id_match:
                            proyecto['id'] = id_match.group(1)
                
                # Detectar tipo
                if texto in ['DIA', 'EIA']:
                    proyecto['tipo'] = texto
                
                # Detectar fecha
                fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
                if fecha_match:
                    proyecto['fecha_presentacion'] = fecha_match.group(1)
                
                # Detectar región
                if 'Región' in texto or 'Metropolitana' in texto:
                    proyecto['region'] = texto
                
                # Detectar empresa
                if i > 0 and len(texto) > 5 and 'S.A' in texto.upper():
                    proyecto['empresa'] = texto
            
            if proyecto.get('titulo'):
                proyecto['fuente'] = 'SEA'
                proyecto['resumen'] = self._generar_resumen_proyecto(proyecto)
                proyecto['relevancia'] = self._calcular_relevancia(proyecto)
                return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de fila: {e}")
        
        return None
    
    def _extraer_proyecto_de_div(self, div) -> Optional[Dict]:
        """Extrae un proyecto desde un div"""
        try:
            proyecto = {}
            
            # Buscar título
            titulo = div.find(['h2', 'h3', 'h4', 'a'])
            if titulo:
                proyecto['titulo'] = titulo.get_text(strip=True)
                if titulo.name == 'a':
                    proyecto['url'] = f"https://seia.sea.gob.cl{titulo.get('href', '')}"
            
            # Buscar otros datos
            texto = div.get_text()
            
            # Tipo
            if 'DIA' in texto:
                proyecto['tipo'] = 'DIA'
            elif 'EIA' in texto:
                proyecto['tipo'] = 'EIA'
            
            # Fecha
            fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', texto)
            if fecha_match:
                proyecto['fecha_presentacion'] = fecha_match.group(1)
            
            # Empresa
            empresa_match = re.search(r'Titular:\s*([^,\n]+)', texto)
            if empresa_match:
                proyecto['empresa'] = empresa_match.group(1).strip()
            
            if proyecto.get('titulo'):
                proyecto['fuente'] = 'SEA'
                proyecto['resumen'] = self._generar_resumen_proyecto(proyecto)
                proyecto['relevancia'] = self._calcular_relevancia(proyecto)
                return proyecto
            
        except Exception as e:
            logger.debug(f"Error extrayendo proyecto de div: {e}")
        
        return None
    
    def _filtrar_proyectos_reales(self, proyectos: List[Dict]) -> List[Dict]:
        """
        Filtra para obtener solo proyectos reales (no noticias ni guías)
        """
        proyectos_reales = []
        
        # Palabras clave que indican que NO es un proyecto real
        palabras_excluir = [
            'guía', 'guías', 'instructivo', 'manual', 'tutorial',
            'observaciones ciudadanas', 'proceso pac', 'noticia',
            'comunicado', 'aviso', 'información', 'consulta pública'
        ]
        
        # Palabras que indican que SÍ es un proyecto real
        palabras_incluir = [
            'planta', 'parque', 'central', 'proyecto', 'construcción',
            'instalación', 'ampliación', 'modificación', 'explotación',
            'minera', 'solar', 'eólico', 'fotovoltaico', 'inmobiliario',
            'tratamiento', 'puerto', 'línea', 'transmisión'
        ]
        
        for proyecto in proyectos:
            titulo = proyecto.get('titulo', '').lower()
            
            # Excluir si contiene palabras de exclusión
            es_excluido = any(palabra in titulo for palabra in palabras_excluir)
            
            # Incluir si contiene palabras de inclusión
            es_proyecto = any(palabra in titulo for palabra in palabras_incluir)
            
            # Es proyecto real si: no está excluido Y (es proyecto O tiene tipo DIA/EIA)
            if not es_excluido and (es_proyecto or proyecto.get('tipo') in ['DIA', 'EIA']):
                proyectos_reales.append(proyecto)
                logger.debug(f"✅ Proyecto REAL: {proyecto.get('titulo', '')[:60]}")
            else:
                logger.debug(f"❌ NO es proyecto: {proyecto.get('titulo', '')[:60]}")
        
        return proyectos_reales
    
    def _generar_resumen_proyecto(self, proyecto: Dict) -> str:
        """Genera un resumen del proyecto"""
        tipo = proyecto.get('tipo', 'Proyecto')
        empresa = proyecto.get('empresa', 'N/A')
        region = proyecto.get('region', '')
        
        resumen = f"{tipo} presentado por {empresa}"
        if region:
            resumen += f" en {region}"
        
        if proyecto.get('inversion_mmusd', 0) > 0:
            resumen += f". Inversión: USD {proyecto['inversion_mmusd']:.1f}MM"
        
        return resumen
    
    def _calcular_relevancia(self, proyecto: Dict) -> float:
        """Calcula la relevancia del proyecto (0-10)"""
        relevancia = 5.0
        
        # Por tipo
        if proyecto.get('tipo') == 'EIA':
            relevancia += 2  # EIA son más complejos
        elif proyecto.get('tipo') == 'DIA':
            relevancia += 1
        
        # Por inversión
        inversion = proyecto.get('inversion_mmusd', 0)
        if inversion > 100:
            relevancia += 2
        elif inversion > 10:
            relevancia += 1
        
        # Por sector
        titulo = proyecto.get('titulo', '').lower()
        if any(sector in titulo for sector in ['minera', 'minero', 'cobre', 'litio']):
            relevancia += 1.5
        if any(sector in titulo for sector in ['energía', 'solar', 'eólico', 'fotovoltaico']):
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
            for p in proyectos:
                if nombre_buscado.lower() in p.get('titulo', '').lower():
                    encontrado = True
                    break
            
            if encontrado:
                logger.info(f"   ✅ {nombre_buscado}")
            else:
                logger.info(f"   ❌ {nombre_buscado} (NO ENCONTRADO)")


def test_scraper():
    """Función de prueba del scraper"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "=" * 80)
    print("🎯 PRUEBA SCRAPER SEA - PROYECTOS REALES")
    print("=" * 80)
    
    scraper = ScraperSEAProyectosReales()
    proyectos = scraper.obtener_datos_sea(dias_atras=7)
    
    print(f"\n✅ Total proyectos REALES encontrados: {len(proyectos)}")
    
    if proyectos:
        print("\n📋 PROYECTOS ENCONTRADOS:")
        print("-" * 80)
        
        for i, p in enumerate(proyectos[:10], 1):
            print(f"\n{i}. {p.get('titulo', 'Sin título')}")
            print(f"   Tipo: {p.get('tipo', 'N/A')}")
            print(f"   Empresa: {p.get('empresa', 'N/A')}")
            print(f"   Fecha: {p.get('fecha_presentacion', 'N/A')}")
            print(f"   Región: {p.get('region', 'N/A')}")
            if p.get('inversion_mmusd', 0) > 0:
                print(f"   Inversión: USD {p['inversion_mmusd']:.1f}MM")
            print(f"   Relevancia: ⭐ {p.get('relevancia', 0):.1f}/10")
    else:
        print("\n⚠️ No se encontraron proyectos")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_scraper()