#!/usr/bin/env python3
"""
Scraper mejorado de CMF que obtiene los enlaces directos correctos
con el formato largo que incluye token + Base64
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional
import re
from pathlib import Path

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScraperCMFMejorado:
    def __init__(self):
        self.base_url = "https://www.cmfchile.cl"
        self.hechos_portada_url = f"{self.base_url}/institucional/hechos/hechos_portada.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def obtener_hechos_fecha(self, fecha: str) -> List[Dict]:
        """
        Alias de obtener_hechos_dia para compatibilidad
        """
        return self.obtener_hechos_dia(fecha)
    
    def obtener_hechos_dia(self, fecha: str) -> List[Dict]:
        """
        Obtiene los hechos esenciales de un día específico
        fecha: formato DD/MM/YYYY
        """
        hechos = []
        
        try:
            # Obtener la página de hechos recientes
            response = self.session.get(self.hechos_portada_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar la tabla de hechos
            tabla = soup.find('table')
            if not tabla:
                logger.error("No se encontró la tabla de hechos")
                return hechos
            
            # Buscar todas las filas
            filas = tabla.find_all('tr')
            
            for fila in filas:
                celdas = fila.find_all('td')
                if len(celdas) >= 4:
                    fecha_hora = celdas[0].text.strip()
                    
                    # Verificar si es de la fecha que buscamos
                    if fecha in fecha_hora:
                        # Buscar el enlace con el formato correcto
                        enlace_elem = celdas[1].find('a')
                        if enlace_elem and 'href' in enlace_elem.attrs:
                            enlace = enlace_elem['href']
                            # Asegurarnos de que el enlace sea absoluto
                            if enlace.startswith('/'):
                                enlace = f"{self.base_url}{enlace}"
                            
                            # Verificar que el enlace tenga el formato correcto (token largo)
                            if 's567=' in enlace and len(enlace.split('s567=')[1].split('&')[0]) > 32:
                                hecho = {
                                    'fecha_hora': fecha_hora,
                                    'numero_documento': celdas[1].text.strip(),
                                    'entidad': celdas[2].text.strip(),
                                    'materia': celdas[3].text.strip(),
                                    'url_pdf': enlace,
                                    'tiene_pdf': True
                                }
                                hechos.append(hecho)
                                logger.info(f"Hecho encontrado: {hecho['entidad']} - {hecho['materia']}")
            
            logger.info(f"Total de hechos encontrados para {fecha}: {len(hechos)}")
            
        except Exception as e:
            logger.error(f"Error al obtener hechos: {str(e)}")
        
        return hechos
    
    def actualizar_json_hechos(self, fecha_buscar: str = None):
        """
        Actualiza el archivo JSON con los hechos del día
        """
        if not fecha_buscar:
            # Por defecto buscar hechos de hoy
            hoy = datetime.now()
            fecha_buscar = hoy.strftime("%d/%m/%Y")
        
        # Convertir fecha para el JSON (formato DD-MM-YYYY)
        fecha_json = fecha_buscar.replace('/', '-')
        
        logger.info(f"Buscando hechos del {fecha_buscar}")
        
        # Obtener hechos del día
        hechos_nuevos = self.obtener_hechos_dia(fecha_buscar)
        
        if not hechos_nuevos:
            logger.warning(f"No se encontraron hechos para {fecha_buscar}")
            return
        
        # Cargar JSON existente
        try:
            json_path = Path(__file__).parent.parent.parent / 'data' / 'hechos_cmf_selenium_reales.json'
            with open(json_path, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except:
            datos = {"hechos": []}
        
        # Actualizar enlaces de hechos existentes o agregar nuevos
        hechos_actualizados = 0
        hechos_agregados = 0
        
        for hecho_nuevo in hechos_nuevos:
            # Buscar si ya existe el hecho para esta entidad y fecha
            encontrado = False
            for i, hecho_existente in enumerate(datos['hechos']):
                if (hecho_existente.get('fecha') == fecha_json and 
                    hecho_existente.get('entidad') == hecho_nuevo['entidad']):
                    # Actualizar el enlace
                    datos['hechos'][i]['url_pdf'] = hecho_nuevo['url_pdf']
                    datos['hechos'][i]['tiene_pdf'] = True
                    datos['hechos'][i]['link_actualizado'] = datetime.now().isoformat()
                    hechos_actualizados += 1
                    encontrado = True
                    break
            
            if not encontrado:
                # Agregar nuevo hecho
                nuevo_registro = {
                    'fecha': fecha_json,
                    'entidad': hecho_nuevo['entidad'],
                    'materia': hecho_nuevo['materia'],
                    'titulo': hecho_nuevo['materia'],
                    'resumen': f"{hecho_nuevo['entidad']} - {hecho_nuevo['materia']} ({fecha_json})",
                    'url_pdf': hecho_nuevo['url_pdf'],
                    'tiene_pdf': True,
                    'relevancia': 5.0,
                    'categoria': 'MODERADO',
                    'es_ipsa': self._es_empresa_ipsa(hecho_nuevo['entidad']),
                    'link_actualizado': datetime.now().isoformat()
                }
                datos['hechos'].append(nuevo_registro)
                hechos_agregados += 1
        
        # Guardar JSON actualizado
        json_path = Path(__file__).parent.parent.parent / 'data' / 'hechos_cmf_selenium_reales.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Actualización completada:")
        logger.info(f"   - Hechos actualizados: {hechos_actualizados}")
        logger.info(f"   - Hechos nuevos agregados: {hechos_agregados}")
    
    def _es_empresa_ipsa(self, entidad: str) -> bool:
        """
        Verifica si la empresa pertenece al IPSA
        """
        empresas_ipsa = [
            'SCOTIABANK', 'BCI', 'BANCO DE CHILE', 'BANCO SANTANDER',
            'FALABELLA', 'CENCOSUD', 'COPEC', 'ENTEL', 'CCU',
            'PARAUCO', 'CMPC', 'COLBUN', 'AGUAS ANDINAS'
        ]
        
        entidad_upper = entidad.upper()
        return any(empresa in entidad_upper for empresa in empresas_ipsa)

def main():
    """
    Función principal
    """
    import sys
    
    scraper = ScraperCMFMejorado()
    
    if len(sys.argv) > 1:
        # Si se proporciona una fecha como argumento
        fecha = sys.argv[1]  # Formato: DD/MM/YYYY
        scraper.actualizar_json_hechos(fecha)
    else:
        # Por defecto, buscar hechos de hoy
        scraper.actualizar_json_hechos()

if __name__ == "__main__":
    main()