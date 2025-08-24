"""
Scraper para SEA/SEIA usando el portal web directamente
Acceso público sin autenticación a proyectos del SEIA
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import re
import json

logger = logging.getLogger(__name__)

class ScraperSEAPortal:
    def __init__(self):
        """
        Inicializa el scraper con el portal web del SEIA
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # URL base del portal SEIA
        self.base_url = "https://seia.sea.gob.cl"
        
        # Estados relevantes para filtrar
        self.estados_relevantes = [
            'Aprobado',
            'Rechazado', 
            'No Admitido a Tramitación',
            'En Calificación',
            'Desistido'
        ]
    
    def buscar_proyectos_recientes(self, dias_atras: int = 1) -> List[Dict]:
        """
        Busca proyectos ingresados o actualizados recientemente
        """
        proyectos = []
        fecha_desde = (datetime.now() - timedelta(days=dias_atras)).strftime('%d/%m/%Y')
        fecha_hasta = datetime.now().strftime('%d/%m/%Y')
        
        # URL de búsqueda avanzada
        search_url = f"{self.base_url}/busqueda/buscarProyectoAction.php"
        
        # Parámetros de búsqueda
        params = {
            'nombre': '',
            'tipo': 'TODOS',
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'estado': 'TODOS',
            'region': 'TODOS',
            'buscar': 'true',
            'pagina': 1
        }
        
        try:
            logger.info(f"🔍 Buscando proyectos desde {fecha_desde} hasta {fecha_hasta}...")
            
            # Realizar búsqueda
            response = self.session.post(search_url, data=params, timeout=30)
            response.raise_for_status()
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tabla de resultados
            tabla = soup.find('table', {'class': ['tabla_datos', 'tabla-busqueda']})
            if not tabla:
                # Intentar encontrar resultados de otra forma
                filas = soup.find_all('tr', {'class': 'fila-proyecto'})
            else:
                filas = tabla.find_all('tr')[1:]  # Saltar header
            
            for fila in filas:
                try:
                    proyecto = self._parsear_fila_proyecto(fila)
                    if proyecto:
                        proyectos.append(proyecto)
                except Exception as e:
                    logger.debug(f"Error parseando fila: {str(e)}")
                    continue
            
            logger.info(f"✅ Encontrados {len(proyectos)} proyectos")
            
        except Exception as e:
            logger.error(f"❌ Error buscando proyectos: {str(e)}")
        
        return proyectos
    
    def obtener_proyectos_destacados(self) -> List[Dict]:
        """
        Obtiene proyectos destacados o recién publicados desde la página principal
        """
        proyectos = []
        
        try:
            logger.info("📋 Obteniendo proyectos destacados...")
            
            # Página principal del SEIA
            response = self.session.get(f"{self.base_url}/", timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar sección de últimos proyectos
            seccion_ultimos = soup.find('div', {'id': 'ultimos-proyectos'})
            if not seccion_ultimos:
                seccion_ultimos = soup.find('div', {'class': 'proyectos-recientes'})
            
            if seccion_ultimos:
                enlaces = seccion_ultimos.find_all('a', href=re.compile(r'/expediente/'))
                
                for enlace in enlaces[:10]:  # Máximo 10 proyectos
                    try:
                        proyecto = self._obtener_detalle_proyecto(enlace.get('href'))
                        if proyecto:
                            proyectos.append(proyecto)
                    except Exception as e:
                        logger.debug(f"Error obteniendo detalle: {str(e)}")
                        continue
            
            logger.info(f"✅ Obtenidos {len(proyectos)} proyectos destacados")
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo proyectos destacados: {str(e)}")
        
        return proyectos
    
    def _parsear_fila_proyecto(self, fila) -> Optional[Dict]:
        """
        Parsea una fila de la tabla de resultados
        """
        try:
            celdas = fila.find_all('td')
            if len(celdas) < 4:
                return None
            
            # Extraer información básica
            nombre = celdas[0].get_text(strip=True)
            tipo = celdas[1].get_text(strip=True) if len(celdas) > 1 else 'N/A'
            titular = celdas[2].get_text(strip=True) if len(celdas) > 2 else 'N/A'
            fecha = celdas[3].get_text(strip=True) if len(celdas) > 3 else 'N/A'
            estado = celdas[4].get_text(strip=True) if len(celdas) > 4 else 'N/A'
            region = celdas[5].get_text(strip=True) if len(celdas) > 5 else 'N/A'
            
            # Buscar enlace al expediente
            enlace = fila.find('a', href=re.compile(r'/expediente/'))
            url = f"{self.base_url}{enlace.get('href')}" if enlace else ''
            
            # Extraer inversión si está disponible
            inversion_texto = 'No especificada'
            for celda in celdas:
                texto = celda.get_text()
                if 'USD' in texto or 'MM' in texto:
                    inversion_texto = texto.strip()
                    break
            
            # Calcular relevancia
            relevancia = self._calcular_relevancia(tipo, estado, inversion_texto)
            
            return {
                'fuente': 'SEA',
                'tipo': tipo,
                'titulo': nombre,
                'titular': titular,
                'fecha': fecha,
                'estado': estado,
                'region': region,
                'inversion': inversion_texto,
                'descripcion': '',
                'relevancia': relevancia,
                'url': url
            }
            
        except Exception as e:
            logger.debug(f"Error parseando fila: {str(e)}")
            return None
    
    def _obtener_detalle_proyecto(self, url_relativa: str) -> Optional[Dict]:
        """
        Obtiene el detalle de un proyecto específico
        """
        try:
            url_completa = f"{self.base_url}{url_relativa}" if not url_relativa.startswith('http') else url_relativa
            
            response = self.session.get(url_completa, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer información del proyecto
            proyecto = {
                'fuente': 'SEA',
                'url': url_completa
            }
            
            # Buscar campos específicos
            campos = {
                'Nombre': 'titulo',
                'Tipo': 'tipo',
                'Titular': 'titular',
                'Fecha': 'fecha',
                'Estado': 'estado',
                'Región': 'region',
                'Inversión': 'inversion',
                'Descripción': 'descripcion'
            }
            
            for campo_buscar, campo_guardar in campos.items():
                elemento = soup.find(text=re.compile(campo_buscar))
                if elemento:
                    contenedor = elemento.parent.parent if elemento.parent else None
                    if contenedor:
                        valor = contenedor.get_text(strip=True).replace(campo_buscar, '').strip(':').strip()
                        proyecto[campo_guardar] = valor
            
            # Valores por defecto
            for campo in campos.values():
                if campo not in proyecto:
                    proyecto[campo] = 'N/A'
            
            # Calcular relevancia
            proyecto['relevancia'] = self._calcular_relevancia(
                proyecto.get('tipo', ''),
                proyecto.get('estado', ''),
                proyecto.get('inversion', '')
            )
            
            return proyecto
            
        except Exception as e:
            logger.debug(f"Error obteniendo detalle de proyecto: {str(e)}")
            return None
    
    def _calcular_relevancia(self, tipo: str, estado: str, inversion: str) -> float:
        """
        Calcula relevancia del proyecto
        """
        relevancia = 5.0
        
        # Por tipo
        if 'EIA' in tipo:
            relevancia += 2.0
        elif 'DIA' in tipo:
            relevancia += 1.0
        
        # Por estado
        if estado == 'Aprobado':
            relevancia += 2.0
        elif estado == 'Rechazado':
            relevancia += 1.5
        elif 'No Admitido' in estado:
            relevancia += 1.0
        
        # Por inversión
        if 'USD' in inversion:
            try:
                # Extraer monto
                monto = re.search(r'([\d,]+)', inversion)
                if monto:
                    valor = float(monto.group(1).replace(',', ''))
                    if valor >= 1000:  # Más de $1,000M USD
                        relevancia += 3.0
                    elif valor >= 500:  # Más de $500M USD
                        relevancia += 2.5
                    elif valor >= 100:  # Más de $100M USD
                        relevancia += 2.0
                    elif valor >= 50:   # Más de $50M USD
                        relevancia += 1.5
            except:
                pass
        
        return min(relevancia, 10.0)
    
    def obtener_datos_sea(self, dias_atras: int = 1) -> List[Dict]:
        """
        Método principal para obtener todos los datos del SEA
        """
        logger.info(f"🌍 Obteniendo datos del SEA (últimos {dias_atras} días)...")
        
        datos = []
        
        # Buscar proyectos recientes
        proyectos = self.buscar_proyectos_recientes(dias_atras)
        datos.extend(proyectos)
        
        # Si no hay resultados, intentar con proyectos destacados
        if not datos:
            logger.info("No se encontraron proyectos recientes, buscando destacados...")
            destacados = self.obtener_proyectos_destacados()
            datos.extend(destacados)
        
        # Ordenar por relevancia
        datos.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
        
        logger.info(f"✅ Total SEA: {len(datos)} proyectos")
        
        return datos


def test_sea_portal():
    """
    Prueba el scraper SEA con el portal web
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🌍 PRUEBA SCRAPER SEA - PORTAL WEB")
    print("="*70)
    
    scraper = ScraperSEAPortal()
    
    # Obtener proyectos de los últimos 7 días
    print("\n📋 Obteniendo proyectos de los últimos 7 días...")
    proyectos = scraper.obtener_datos_sea(dias_atras=7)
    
    if proyectos:
        print(f"\n✅ Obtenidos {len(proyectos)} proyectos del SEA")
        
        print("\n" + "-"*70)
        print("📋 ÚLTIMOS PROYECTOS SEIA")
        print("-"*70)
        
        for i, proyecto in enumerate(proyectos[:5], 1):
            print(f"\n{i}. {proyecto['titulo']}")
            print(f"   📅 {proyecto['fecha']} | 🏢 {proyecto['titular']}")
            print(f"   📍 {proyecto['region']}")
            print(f"   💰 {proyecto['inversion']}")
            print(f"   📊 Estado: {proyecto['estado']}")
            print(f"   📝 {proyecto['tipo']}")
            if proyecto['descripcion'] and proyecto['descripcion'] != 'N/A':
                print(f"   💬 {proyecto['descripcion'][:100]}...")
            print(f"   ⭐ Relevancia: {proyecto['relevancia']:.1f}/10")
            if proyecto['url']:
                print(f"   🔗 {proyecto['url']}")
    else:
        print("\n⚠️ No se obtuvieron proyectos")
        print("Intentando con proyectos destacados...")
        
        destacados = scraper.obtener_proyectos_destacados()
        if destacados:
            print(f"\n✅ Obtenidos {len(destacados)} proyectos destacados")
            for i, proyecto in enumerate(destacados[:3], 1):
                print(f"\n{i}. {proyecto['titulo']}")
                print(f"   Estado: {proyecto['estado']}")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    test_sea_portal()