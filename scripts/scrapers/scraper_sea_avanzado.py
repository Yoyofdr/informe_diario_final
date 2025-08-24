"""
Scraper avanzado para SEA/SEIA
Usa el buscador avanzado y filtros por fecha
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import json
from typing import List, Dict, Optional
from pathlib import Path
import re
from urllib.parse import urlencode, urljoin

logger = logging.getLogger(__name__)

class ScraperSEAAvanzado:
    """
    Scraper para el Sistema de Evaluación de Impacto Ambiental (SEIA)
    Usa el buscador avanzado con filtros específicos
    """
    
    def __init__(self, cache_dir: str = None):
        self.base_url = "https://seia.sea.gob.cl"
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoAction.php"
        self.cache_dir = cache_dir or Path("/tmp/sea_cache")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-CL,es;q=0.9',
            'Referer': 'https://seia.sea.gob.cl/busqueda/buscarProyecto.php'
        })
        
        # Estados de interés para el informe
        self.estados_relevantes = [
            'Aprobado',           # RCA aprobada
            'Rechazado',          # RCA rechazada
            'No admitido',        # No admitido a tramitación
            'Desistido',          # Titular desistió
            'No calificado'       # No calificado
        ]
        
        # Sectores prioritarios (para cálculo de relevancia)
        self.sectores_prioritarios = {
            'minero': 3.0,
            'energía': 2.5,
            'infraestructura': 2.0,
            'inmobiliario': 1.5,
            'industrial': 1.5,
            'saneamiento': 1.0,
            'agropecuario': 1.0
        }
    
    def obtener_proyectos_dia(self, fecha: datetime = None) -> Dict[str, List[Dict]]:
        """
        Obtiene proyectos del día especificado
        
        Args:
            fecha: Fecha a consultar (por defecto ayer)
            
        Returns:
            Dict con proyectos organizados por tipo
        """
        if not fecha:
            fecha = datetime.now() - timedelta(days=1)
        
        resultado = {
            'proyectos_calificados': [],  # Aprobados y rechazados
            'proyectos_pac': [],          # En Participación Ciudadana
            'metadata': {
                'fecha_consulta': datetime.now().isoformat(),
                'fecha_datos': fecha.isoformat(),
                'fuente': 'SEA/SEIA Buscador Avanzado'
            }
        }
        
        # Buscar proyectos con RCA del día
        for estado in self.estados_relevantes:
            proyectos = self._buscar_proyectos_por_fecha_estado(fecha, estado)
            resultado['proyectos_calificados'].extend(proyectos)
        
        # Buscar proyectos en PAC (Participación Ciudadana)
        proyectos_pac = self._buscar_proyectos_pac(fecha)
        resultado['proyectos_pac'] = proyectos_pac
        
        # Deduplicar por ID
        resultado['proyectos_calificados'] = self._deduplicar_proyectos(
            resultado['proyectos_calificados']
        )
        
        logger.info(f"✅ Obtenidos {len(resultado['proyectos_calificados'])} proyectos calificados")
        logger.info(f"✅ Obtenidos {len(resultado['proyectos_pac'])} proyectos en PAC")
        
        return resultado
    
    def _buscar_proyectos_por_fecha_estado(self, fecha: datetime, estado: str) -> List[Dict]:
        """
        Busca proyectos por fecha de calificación y estado
        """
        try:
            # Preparar parámetros para el buscador avanzado
            params = {
                'tipo_busqueda': 'avanzada',
                'nombre_proyecto': '',
                'titular': '',
                'tipo_proyecto': '',  # Todos los tipos
                'region': '',         # Todas las regiones
                'comuna': '',
                'fecha_presentacion_desde': '',
                'fecha_presentacion_hasta': '',
                'fecha_calificacion_desde': fecha.strftime('%d/%m/%Y'),
                'fecha_calificacion_hasta': fecha.strftime('%d/%m/%Y'),
                'estado': estado,
                'buscar': '1',
                'pagina': '1',
                'registros_por_pagina': '100'  # Máximo por página
            }
            
            logger.info(f"🔍 Buscando proyectos SEA - Estado: {estado}, Fecha: {fecha:%d/%m/%Y}")
            
            response = self.session.post(self.search_url, data=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tabla de resultados
            tabla = soup.find('table', {'class': ['tabla_datos', 'table', 'listado']})
            if not tabla:
                # Intentar encontrar cualquier tabla con proyectos
                tablas = soup.find_all('table')
                for t in tablas:
                    if 'proyecto' in str(t).lower() or 'nombre' in str(t).lower():
                        tabla = t
                        break
            
            if not tabla:
                logger.warning(f"No se encontraron resultados para estado '{estado}'")
                return []
            
            proyectos = []
            filas = tabla.find_all('tr')[1:]  # Saltar encabezado
            
            for fila in filas:
                proyecto = self._extraer_proyecto_de_fila(fila, estado)
                if proyecto:
                    proyectos.append(proyecto)
            
            logger.info(f"  → Encontrados {len(proyectos)} proyectos con estado '{estado}'")
            return proyectos
            
        except Exception as e:
            logger.error(f"❌ Error buscando proyectos SEA: {str(e)}")
            return []
    
    def _buscar_proyectos_pac(self, fecha: datetime) -> List[Dict]:
        """
        Busca proyectos en Participación Ciudadana (PAC)
        """
        try:
            # URL específica para PAC
            pac_url = f"{self.base_url}/externos/proyectos_en_pac.php"
            
            response = self.session.get(pac_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            proyectos_pac = []
            
            # Buscar proyectos en PAC
            tabla = soup.find('table', {'class': ['tabla_datos', 'table']})
            if tabla:
                filas = tabla.find_all('tr')[1:]
                
                for fila in filas:
                    proyecto = self._extraer_proyecto_pac(fila)
                    if proyecto:
                        # Verificar si el PAC inició recientemente
                        if self._es_pac_reciente(proyecto, fecha):
                            proyectos_pac.append(proyecto)
            
            return proyectos_pac
            
        except Exception as e:
            logger.error(f"Error obteniendo proyectos PAC: {str(e)}")
            return []
    
    def _extraer_proyecto_de_fila(self, fila, estado: str) -> Optional[Dict]:
        """
        Extrae información de un proyecto desde una fila de tabla
        """
        try:
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) < 4:
                return None
            
            # Buscar enlace al proyecto
            enlace = fila.find('a')
            if not enlace:
                return None
            
            # Extraer información básica
            nombre = enlace.text.strip()
            href = enlace.get('href', '')
            
            # Extraer ID del proyecto
            id_proyecto = self._extraer_id_proyecto(href)
            
            # URL completa
            url_proyecto = urljoin(self.base_url, href)
            
            # Extraer otros campos (posiciones pueden variar)
            proyecto = {
                'id': id_proyecto,
                'nombre': nombre,
                'url': url_proyecto,
                'estado': estado,
                'fecha_calificacion': self._buscar_fecha_en_fila(fila),
                'tipo': self._extraer_tipo_proyecto(fila),
                'titular': self._extraer_titular(fila),
                'region': self._extraer_region(fila),
                'inversion_mmusd': self._extraer_inversion(fila),
                'fuente': 'SEA/SEIA'
            }
            
            # Obtener detalles adicionales si es necesario
            proyecto['sector'] = self._identificar_sector(proyecto['tipo'], nombre)
            proyecto['relevancia'] = self._calcular_relevancia(proyecto)
            
            return proyecto
            
        except Exception as e:
            logger.error(f"Error extrayendo proyecto: {str(e)}")
            return None
    
    def _extraer_proyecto_pac(self, fila) -> Optional[Dict]:
        """
        Extrae información de un proyecto en PAC
        """
        try:
            celdas = fila.find_all(['td', 'th'])
            enlace = fila.find('a')
            
            if not enlace:
                return None
            
            return {
                'id': self._extraer_id_proyecto(enlace.get('href', '')),
                'nombre': enlace.text.strip(),
                'url': urljoin(self.base_url, enlace.get('href', '')),
                'tipo_pac': 'PAC',
                'fecha_inicio_pac': self._buscar_fecha_en_fila(fila),
                'fecha_termino_pac': self._buscar_fecha_termino_pac(fila),
                'titular': self._extraer_titular(fila),
                'region': self._extraer_region(fila),
                'fuente': 'SEA/SEIA PAC'
            }
            
        except:
            return None
    
    def _extraer_id_proyecto(self, url: str) -> str:
        """
        Extrae el ID del proyecto de la URL
        """
        # Buscar patrones comunes
        patterns = [
            r'id_expediente=(\d+)',
            r'codigo=([A-Z0-9-]+)',
            r'proyecto/(\d+)',
            r'ficha/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Si no encuentra, usar hash de la URL
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:10]
    
    def _buscar_fecha_en_fila(self, fila) -> str:
        """
        Busca una fecha en la fila
        """
        texto = fila.text
        
        # Buscar fechas en formato DD/MM/YYYY o DD-MM-YYYY
        patron_fecha = r'\d{1,2}[/-]\d{1,2}[/-]\d{4}'
        match = re.search(patron_fecha, texto)
        
        if match:
            return match.group()
        
        return ""
    
    def _buscar_fecha_termino_pac(self, fila) -> str:
        """
        Busca la fecha de término del PAC
        """
        # Buscar segunda fecha en la fila (primera es inicio)
        texto = fila.text
        fechas = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', texto)
        
        if len(fechas) >= 2:
            return fechas[1]  # Segunda fecha es término
        
        return ""
    
    def _extraer_tipo_proyecto(self, fila) -> str:
        """
        Extrae el tipo de proyecto
        """
        # Buscar en celdas típicas de tipo
        for celda in fila.find_all(['td', 'th']):
            texto = celda.text.strip().lower()
            
            # Palabras clave de tipos de proyecto
            tipos = ['minero', 'energía', 'puerto', 'inmobiliario', 'industrial',
                    'agrícola', 'acuícola', 'infraestructura', 'saneamiento']
            
            for tipo in tipos:
                if tipo in texto:
                    return tipo.capitalize()
        
        return "Otros"
    
    def _extraer_titular(self, fila) -> str:
        """
        Extrae el titular del proyecto
        """
        # Buscar patrones de empresa
        texto = fila.text
        
        # Buscar S.A., Ltda, SpA, etc.
        patron_empresa = r'([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s&]+(?:S\.A\.|LTDA|SpA|EIRL|S\.P\.A\.))'
        match = re.search(patron_empresa, texto)
        
        if match:
            return match.group(1).strip()
        
        # Buscar en celdas específicas
        celdas = fila.find_all(['td', 'th'])
        for i, celda in enumerate(celdas):
            if 'titular' in celda.text.lower() and i + 1 < len(celdas):
                return celdas[i + 1].text.strip()
        
        return "No especificado"
    
    def _extraer_region(self, fila) -> str:
        """
        Extrae la región del proyecto
        """
        texto = fila.text
        
        # Lista de regiones de Chile
        regiones = [
            'Arica y Parinacota', 'Tarapacá', 'Antofagasta', 'Atacama',
            'Coquimbo', 'Valparaíso', "O'Higgins", 'Maule', 'Ñuble',
            'Biobío', 'Araucanía', 'Los Ríos', 'Los Lagos', 'Aysén',
            'Magallanes', 'Metropolitana'
        ]
        
        for region in regiones:
            if region.lower() in texto.lower():
                return f"Región de {region}"
        
        # Buscar por número romano
        patron_region = r'Región\s+([IVX]+)'
        match = re.search(patron_region, texto)
        if match:
            return f"Región {match.group(1)}"
        
        return ""
    
    def _extraer_inversion(self, fila) -> float:
        """
        Extrae el monto de inversión en MMUSD
        """
        texto = fila.text
        
        # Buscar montos en USD
        patrones = [
            r'USD?\s*([\d,]+(?:\.\d+)?)\s*(?:MM|millones)',
            r'US\$\s*([\d,]+(?:\.\d+)?)\s*(?:MM|millones)',
            r'([\d,]+(?:\.\d+)?)\s*MMUSD'
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                try:
                    monto = match.group(1).replace(',', '.')
                    return float(monto)
                except:
                    pass
        
        return 0.0
    
    def _identificar_sector(self, tipo: str, nombre: str) -> str:
        """
        Identifica el sector del proyecto
        """
        texto = f"{tipo} {nombre}".lower()
        
        # Mapeo de palabras clave a sectores
        sectores = {
            'minero': ['minera', 'mina', 'extracción', 'cobre', 'litio', 'oro'],
            'energía': ['solar', 'eólico', 'fotovoltaico', 'central', 'generación', 'transmisión'],
            'infraestructura': ['carretera', 'puente', 'aeropuerto', 'puerto', 'vial'],
            'inmobiliario': ['inmobiliario', 'habitacional', 'edificio', 'condominio'],
            'industrial': ['planta', 'fábrica', 'procesamiento', 'industrial'],
            'saneamiento': ['agua', 'alcantarillado', 'tratamiento', 'residuos'],
            'agropecuario': ['agrícola', 'ganadero', 'plantación', 'cultivo']
        }
        
        for sector, keywords in sectores.items():
            for keyword in keywords:
                if keyword in texto:
                    return sector
        
        return 'otros'
    
    def _calcular_relevancia(self, proyecto: Dict) -> float:
        """
        Calcula la relevancia del proyecto
        """
        score = 0.0
        
        # Factor inversión (más importante)
        inversion = proyecto.get('inversion_mmusd', 0)
        if inversion >= 500:
            score += 10
        elif inversion >= 200:
            score += 8
        elif inversion >= 100:
            score += 6
        elif inversion >= 50:
            score += 4
        elif inversion >= 10:
            score += 2
        else:
            score += 1
        
        # Factor sector
        sector = proyecto.get('sector', 'otros')
        score += self.sectores_prioritarios.get(sector, 0.5)
        
        # Factor estado
        estado = proyecto.get('estado', '').lower()
        if 'rechazado' in estado:
            score += 2  # Los rechazos son noticia
        elif 'aprobado' in estado:
            score += 1
        
        # Normalizar a escala 0-10
        return min(score, 10.0)
    
    def _es_pac_reciente(self, proyecto_pac: Dict, fecha_referencia: datetime) -> bool:
        """
        Verifica si un PAC es reciente (iniciado en los últimos días)
        """
        fecha_inicio = proyecto_pac.get('fecha_inicio_pac', '')
        if not fecha_inicio:
            return False
        
        try:
            # Parsear fecha
            for formato in ['%d/%m/%Y', '%d-%m-%Y']:
                try:
                    fecha_pac = datetime.strptime(fecha_inicio, formato)
                    # Considerar reciente si es de los últimos 3 días
                    dias_diferencia = (fecha_referencia - fecha_pac).days
                    return 0 <= dias_diferencia <= 3
                except:
                    continue
        except:
            pass
        
        return False
    
    def _deduplicar_proyectos(self, proyectos: List[Dict]) -> List[Dict]:
        """
        Elimina proyectos duplicados basándose en el ID
        """
        vistos = set()
        unicos = []
        
        for proyecto in proyectos:
            id_proyecto = proyecto.get('id')
            if id_proyecto and id_proyecto not in vistos:
                vistos.add(id_proyecto)
                unicos.append(proyecto)
        
        return unicos
    
    def formatear_para_informe(self, datos: Dict) -> Dict:
        """
        Formatea los datos para el informe diario
        """
        resultado = {
            'proyectos_principales': [],
            'proyectos_pac': [],
            'resumen_ejecutivo': {}
        }
        
        # Procesar proyectos calificados
        for proyecto in datos.get('proyectos_calificados', []):
            proyecto_formateado = {
                'fuente': 'SEA',
                'tipo': 'rca',
                'titulo': proyecto['nombre'],
                'empresa': proyecto.get('titular', 'No especificado'),
                'fecha': proyecto.get('fecha_calificacion', ''),
                'estado': proyecto.get('estado', ''),
                'region': proyecto.get('region', ''),
                'inversion_mmusd': proyecto.get('inversion_mmusd', 0),
                'sector': proyecto.get('sector', 'otros'),
                'url': proyecto.get('url', ''),
                'resumen': self._generar_resumen_proyecto(proyecto),
                'relevancia': proyecto.get('relevancia', 0),
                'badge_text': self._obtener_badge_estado(proyecto['estado']),
                'badge_color': self._obtener_color_estado(proyecto['estado'])
            }
            resultado['proyectos_principales'].append(proyecto_formateado)
        
        # Procesar PAC
        for pac in datos.get('proyectos_pac', []):
            pac_formateado = {
                'fuente': 'SEA',
                'tipo': 'pac',
                'titulo': pac['nombre'],
                'empresa': pac.get('titular', 'No especificado'),
                'fecha_inicio': pac.get('fecha_inicio_pac', ''),
                'fecha_termino': pac.get('fecha_termino_pac', ''),
                'region': pac.get('region', ''),
                'url': pac.get('url', ''),
                'resumen': f"Proceso de Participación Ciudadana abierto hasta {pac.get('fecha_termino_pac', 'fecha no especificada')}",
                'badge_text': 'PAC ABIERTO',
                'badge_color': '#3b82f6'  # Azul
            }
            resultado['proyectos_pac'].append(pac_formateado)
        
        # Ordenar por relevancia
        resultado['proyectos_principales'].sort(
            key=lambda x: x['relevancia'], 
            reverse=True
        )
        
        # Generar resumen ejecutivo
        resultado['resumen_ejecutivo'] = self._generar_resumen_ejecutivo(resultado)
        
        return resultado
    
    def _generar_resumen_proyecto(self, proyecto: Dict) -> str:
        """
        Genera un resumen conciso del proyecto
        """
        partes = []
        
        # Estado
        estado = proyecto.get('estado', '').upper()
        partes.append(estado)
        
        # Tipo y sector
        if proyecto.get('sector'):
            partes.append(f"Proyecto {proyecto['sector']}")
        elif proyecto.get('tipo'):
            partes.append(f"Proyecto de {proyecto['tipo']}")
        
        # Inversión
        if proyecto.get('inversion_mmusd'):
            partes.append(f"Inversión: USD {proyecto['inversion_mmusd']:.1f}MM")
        
        # Región
        if proyecto.get('region'):
            partes.append(f"en {proyecto['region']}")
        
        return ". ".join(partes)
    
    def _obtener_badge_estado(self, estado: str) -> str:
        """
        Obtiene el texto del badge según el estado
        """
        badges = {
            'Aprobado': '✅ APROBADO',
            'Rechazado': '❌ RECHAZADO',
            'No admitido': '⚠️ NO ADMITIDO',
            'Desistido': '↩️ DESISTIDO',
            'No calificado': '❓ NO CALIFICADO'
        }
        return badges.get(estado, estado.upper())
    
    def _obtener_color_estado(self, estado: str) -> str:
        """
        Obtiene el color según el estado (todos verdes según requisito)
        """
        # Por requisito del usuario: todo en verde
        return '#16a34a'
    
    def _generar_resumen_ejecutivo(self, datos_formateados: Dict) -> Dict:
        """
        Genera un resumen ejecutivo de los datos
        """
        proyectos = datos_formateados['proyectos_principales']
        pacs = datos_formateados['proyectos_pac']
        
        # Contar por estado
        aprobados = len([p for p in proyectos if 'APROBADO' in p.get('badge_text', '')])
        rechazados = len([p for p in proyectos if 'RECHAZADO' in p.get('badge_text', '')])
        
        # Sumar inversión
        inversion_total = sum(p.get('inversion_mmusd', 0) for p in proyectos)
        
        return {
            'total_proyectos': len(proyectos),
            'aprobados': aprobados,
            'rechazados': rechazados,
            'inversion_total_mmusd': inversion_total,
            'pac_abiertos': len(pacs),
            'texto': f"Ayer: {len(proyectos)} proyectos (USD {inversion_total:.0f}MM), {len(pacs)} PAC abiertos"
        }


def test_scraper_sea():
    """
    Función de prueba del scraper SEA avanzado
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🌍 PRUEBA SCRAPER SEA AVANZADO")
    print("="*70)
    
    scraper = ScraperSEAAvanzado()
    
    # Obtener proyectos del día anterior
    print("\n📊 Obteniendo proyectos SEA del día anterior...")
    fecha_ayer = datetime.now() - timedelta(days=1)
    datos = scraper.obtener_proyectos_dia(fecha_ayer)
    
    # Mostrar resumen
    print(f"\n✅ Datos obtenidos para {fecha_ayer:%d/%m/%Y}:")
    print(f"  - Proyectos calificados: {len(datos.get('proyectos_calificados', []))}")
    print(f"  - Proyectos en PAC: {len(datos.get('proyectos_pac', []))}")
    
    # Formatear para informe
    print("\n📝 Formateando para informe...")
    datos_formateados = scraper.formatear_para_informe(datos)
    
    # Mostrar resumen ejecutivo
    resumen = datos_formateados.get('resumen_ejecutivo', {})
    print(f"\n📊 RESUMEN EJECUTIVO:")
    print(f"  {resumen.get('texto', '')}")
    
    # Mostrar primeros proyectos
    proyectos = datos_formateados.get('proyectos_principales', [])
    if proyectos:
        print(f"\n📋 Top {min(3, len(proyectos))} proyectos más relevantes:")
        for i, proyecto in enumerate(proyectos[:3], 1):
            print(f"\n{i}. {proyecto['badge_text']} {proyecto['titulo']}")
            print(f"   🏢 {proyecto['empresa']}")
            print(f"   📅 {proyecto['fecha']}")
            print(f"   📝 {proyecto['resumen']}")
            print(f"   ⭐ Relevancia: {proyecto['relevancia']:.1f}/10")
    
    # Mostrar PACs
    pacs = datos_formateados.get('proyectos_pac', [])
    if pacs:
        print(f"\n🗣️ Procesos de Participación Ciudadana abiertos:")
        for pac in pacs[:2]:
            print(f"\n  • {pac['titulo']}")
            print(f"    Cierra: {pac['fecha_termino']}")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    test_scraper_sea()