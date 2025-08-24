"""
Scraper para el Servicio de Evaluación Ambiental (SEA)
Obtiene Resoluciones de Calificación Ambiental (RCA) recientes
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import json
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class ScraperSEA:
    def __init__(self):
        self.base_url = "https://seia.sea.gob.cl"
        self.search_url = f"{self.base_url}/busqueda/buscarProyectoAction.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9'
        })
    
    def obtener_proyectos_recientes(self, dias_atras: int = 7) -> List[Dict]:
        """
        Obtiene proyectos con RCA (aprobados o rechazados) en los últimos días
        
        Args:
            dias_atras: Número de días hacia atrás para buscar
            
        Returns:
            Lista de proyectos con sus detalles
        """
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=dias_atras)
        
        proyectos = []
        
        # Buscar proyectos aprobados
        proyectos.extend(self._buscar_proyectos(
            fecha_desde, fecha_hasta, 
            estado='Aprobado'
        ))
        
        # Buscar proyectos rechazados
        proyectos.extend(self._buscar_proyectos(
            fecha_desde, fecha_hasta,
            estado='Rechazado'
        ))
        
        # Buscar proyectos con RCA (pueden tener otros estados)
        proyectos.extend(self._buscar_proyectos(
            fecha_desde, fecha_hasta,
            estado='No Admitido'
        ))
        
        return self._eliminar_duplicados(proyectos)
    
    def _buscar_proyectos(self, fecha_desde: datetime, fecha_hasta: datetime, 
                         estado: str = None) -> List[Dict]:
        """
        Busca proyectos en el SEA con filtros específicos
        """
        try:
            # Preparar parámetros de búsqueda
            params = {
                'nombre': '',
                'titular': '',
                'tipoproyecto': '',
                'region': '',
                'comuna': '',
                'fechaingreso_desde': '',
                'fechaingreso_hasta': '',
                'fechacalificacion_desde': fecha_desde.strftime('%d/%m/%Y'),
                'fechacalificacion_hasta': fecha_hasta.strftime('%d/%m/%Y'),
                'estado': estado if estado else '',
                'buscar': 'true',
                'popup': ''
            }
            
            logger.info(f"🔍 Buscando proyectos SEA - Estado: {estado}, Fechas: {fecha_desde:%d/%m/%Y} - {fecha_hasta:%d/%m/%Y}")
            
            # Permitir redirecciones
            response = self.session.post(self.search_url, data=params, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tabla de resultados - intentar varios selectores
            tabla = soup.find('table', {'class': 'tabla_datos'})
            if not tabla:
                # Intentar otros selectores comunes
                tabla = soup.find('table', {'id': 'tabla_resultado'})
            if not tabla:
                tabla = soup.find('table', {'class': 'table'})
            if not tabla:
                # Buscar cualquier tabla que tenga más de 5 filas
                todas_tablas = soup.find_all('table')
                for t in todas_tablas:
                    if len(t.find_all('tr')) > 5:
                        tabla = t
                        break
            
            if not tabla:
                logger.warning(f"No se encontró tabla de resultados. HTML tiene {len(response.text)} caracteres")
                # Guardar HTML para depuración
                with open('/tmp/sea_response.html', 'w') as f:
                    f.write(response.text[:5000])
                logger.info("HTML guardado en /tmp/sea_response.html para depuración")
                return []
            
            proyectos = []
            filas = tabla.find_all('tr')[1:]  # Saltar encabezado
            
            for fila in filas:
                celdas = fila.find_all('td')
                if len(celdas) >= 7:
                    proyecto = self._extraer_datos_proyecto(celdas)
                    if proyecto:
                        proyectos.append(proyecto)
            
            logger.info(f"✅ Encontrados {len(proyectos)} proyectos con estado '{estado}'")
            return proyectos
            
        except Exception as e:
            logger.error(f"❌ Error buscando proyectos SEA: {str(e)}")
            return []
    
    def _extraer_datos_proyecto(self, celdas) -> Optional[Dict]:
        """
        Extrae datos de un proyecto desde las celdas de la tabla
        """
        try:
            # Extraer enlace al proyecto
            enlace = celdas[1].find('a')
            if not enlace:
                return None
            
            nombre = enlace.text.strip()
            href = enlace.get('href', '')
            
            # Extraer ID del proyecto de la URL
            proyecto_id = None
            if 'codigo=' in href:
                proyecto_id = href.split('codigo=')[1].split('&')[0]
            
            # Construir URL completa
            if href.startswith('/'):
                url_proyecto = f"{self.base_url}{href}"
            else:
                url_proyecto = f"{self.base_url}/{href}"
            
            proyecto = {
                'id': proyecto_id,
                'nombre': nombre,
                'url': url_proyecto,
                'tipo': celdas[2].text.strip() if len(celdas) > 2 else '',
                'region': celdas[3].text.strip() if len(celdas) > 3 else '',
                'titular': celdas[4].text.strip() if len(celdas) > 4 else '',
                'inversion_mmusd': self._extraer_inversion(celdas[5].text if len(celdas) > 5 else ''),
                'fecha_calificacion': celdas[6].text.strip() if len(celdas) > 6 else '',
                'estado': celdas[7].text.strip() if len(celdas) > 7 else ''
            }
            
            return proyecto
            
        except Exception as e:
            logger.error(f"Error extrayendo datos de proyecto: {str(e)}")
            return None
    
    def _extraer_inversion(self, texto: str) -> Optional[float]:
        """
        Extrae el monto de inversión del texto
        """
        try:
            # Limpiar y convertir a número
            texto = texto.strip().replace(',', '.')
            match = re.search(r'[\d.]+', texto)
            if match:
                return float(match.group())
        except:
            pass
        return None
    
    def obtener_detalles_proyecto(self, proyecto: Dict) -> Dict:
        """
        Obtiene detalles adicionales de un proyecto específico
        """
        try:
            if not proyecto.get('url'):
                return proyecto
            
            response = self.session.get(proyecto['url'], timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar RCA y otros documentos importantes
            proyecto['rca'] = self._buscar_rca(soup)
            proyecto['descripcion'] = self._extraer_descripcion(soup)
            proyecto['impactos'] = self._extraer_impactos(soup)
            
            return proyecto
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles de proyecto {proyecto.get('nombre')}: {str(e)}")
            return proyecto
    
    def _buscar_rca(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Busca la Resolución de Calificación Ambiental en la página del proyecto
        """
        try:
            # Buscar enlaces a RCA
            for link in soup.find_all('a'):
                texto = link.text.lower()
                href = link.get('href', '')
                
                if 'rca' in texto or 'resolución de calificación' in texto:
                    return {
                        'titulo': link.text.strip(),
                        'url': f"{self.base_url}{href}" if href.startswith('/') else href
                    }
        except:
            pass
        return None
    
    def _extraer_descripcion(self, soup: BeautifulSoup) -> str:
        """
        Extrae la descripción del proyecto
        """
        try:
            # Buscar en diferentes posibles ubicaciones
            for tag in ['div', 'td', 'p']:
                elementos = soup.find_all(tag)
                for elem in elementos:
                    texto = elem.text.strip()
                    if 'descripción' in texto.lower() and len(texto) > 100:
                        return texto[:500]  # Limitar longitud
        except:
            pass
        return ""
    
    def _extraer_impactos(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae información sobre impactos ambientales
        """
        impactos = []
        try:
            keywords = ['impacto', 'emisión', 'contaminación', 'residuo', 'efluente']
            
            for keyword in keywords:
                for elem in soup.find_all(text=re.compile(keyword, re.IGNORECASE)):
                    padre = elem.parent
                    if padre and padre.name in ['p', 'div', 'td', 'li']:
                        texto = padre.text.strip()[:200]
                        if texto and texto not in impactos:
                            impactos.append(texto)
                            if len(impactos) >= 3:  # Limitar cantidad
                                break
        except:
            pass
        return impactos
    
    def _eliminar_duplicados(self, proyectos: List[Dict]) -> List[Dict]:
        """
        Elimina proyectos duplicados basándose en el ID
        """
        vistos = set()
        unicos = []
        
        for proyecto in proyectos:
            id_proyecto = proyecto.get('id') or proyecto.get('nombre')
            if id_proyecto not in vistos:
                vistos.add(id_proyecto)
                unicos.append(proyecto)
        
        return unicos
    
    def formatear_para_informe(self, proyectos: List[Dict]) -> List[Dict]:
        """
        Formatea los proyectos para incluir en el informe diario
        """
        formateados = []
        
        for proyecto in proyectos:
            # Solo incluir proyectos significativos
            if proyecto.get('inversion_mmusd', 0) < 1:  # Menos de 1 MMUSD
                continue
            
            formateado = {
                'fuente': 'SEA',
                'tipo': 'RCA',
                'titulo': proyecto['nombre'],
                'empresa': proyecto.get('titular', 'No especificado'),
                'fecha': proyecto.get('fecha_calificacion', ''),
                'estado': proyecto.get('estado', ''),
                'region': proyecto.get('region', ''),
                'inversion_mmusd': proyecto.get('inversion_mmusd'),
                'url': proyecto.get('url', ''),
                'resumen': self._generar_resumen(proyecto),
                'relevancia': self._calcular_relevancia(proyecto)
            }
            
            formateados.append(formateado)
        
        # Ordenar por relevancia
        formateados.sort(key=lambda x: x['relevancia'], reverse=True)
        
        return formateados[:10]  # Limitar a 10 más relevantes
    
    def _generar_resumen(self, proyecto: Dict) -> str:
        """
        Genera un resumen del proyecto
        """
        partes = []
        
        # Estado
        estado = proyecto.get('estado', '').lower()
        if 'aprob' in estado:
            partes.append("✅ APROBADO")
        elif 'rechaz' in estado:
            partes.append("❌ RECHAZADO")
        elif 'no admit' in estado:
            partes.append("⚠️ NO ADMITIDO")
        
        # Tipo de proyecto
        if proyecto.get('tipo'):
            partes.append(f"Proyecto de {proyecto['tipo']}")
        
        # Inversión
        if proyecto.get('inversion_mmusd'):
            partes.append(f"Inversión: USD {proyecto['inversion_mmusd']:.1f}MM")
        
        # Región
        if proyecto.get('region'):
            partes.append(f"en {proyecto['region']}")
        
        # Descripción adicional
        if proyecto.get('descripcion'):
            partes.append(proyecto['descripcion'][:100])
        
        return ". ".join(partes)
    
    def _calcular_relevancia(self, proyecto: Dict) -> float:
        """
        Calcula un score de relevancia para priorizar proyectos
        """
        score = 0.0
        
        # Inversión (más importante)
        inversion = proyecto.get('inversion_mmusd', 0)
        if inversion > 100:
            score += 10
        elif inversion > 50:
            score += 7
        elif inversion > 10:
            score += 5
        elif inversion > 5:
            score += 3
        else:
            score += 1
        
        # Estado
        estado = proyecto.get('estado', '').lower()
        if 'aprob' in estado:
            score += 3
        elif 'rechaz' in estado:
            score += 2  # También importante saber rechazos
        
        # Tipo de proyecto (sectores críticos)
        tipo = proyecto.get('tipo', '').lower()
        sectores_criticos = ['minero', 'energía', 'puerto', 'industrial', 'inmobiliario']
        for sector in sectores_criticos:
            if sector in tipo:
                score += 2
                break
        
        return score


def test_scraper_sea():
    """
    Función de prueba del scraper SEA
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = ScraperSEA()
    
    # Obtener proyectos de los últimos 30 días para tener más resultados
    print("\n=== PRUEBA SCRAPER SEA ===\n")
    print("Buscando proyectos con RCA de los últimos 30 días...")
    
    proyectos = scraper.obtener_proyectos_recientes(dias_atras=30)
    
    if proyectos:
        print(f"\n✅ Encontrados {len(proyectos)} proyectos\n")
        
        # Obtener detalles del primer proyecto
        if len(proyectos) > 0:
            print("Obteniendo detalles del primer proyecto...")
            proyecto_detallado = scraper.obtener_detalles_proyecto(proyectos[0])
            
            print("\n--- EJEMPLO DE PROYECTO ---")
            print(json.dumps(proyecto_detallado, indent=2, ensure_ascii=False))
        
        # Formatear para informe
        print("\n--- PROYECTOS FORMATEADOS PARA INFORME ---")
        formateados = scraper.formatear_para_informe(proyectos)
        
        for i, proyecto in enumerate(formateados[:5], 1):
            print(f"\n{i}. {proyecto['titulo']}")
            print(f"   {proyecto['resumen']}")
            print(f"   Relevancia: {proyecto['relevancia']:.1f}")
    else:
        print("❌ No se encontraron proyectos")


if __name__ == "__main__":
    test_scraper_sea()