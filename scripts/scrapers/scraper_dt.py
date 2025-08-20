#!/usr/bin/env python3
"""
Scraper para obtener dictámenes y ordinarios de la Dirección del Trabajo
Similar al scraper del SII - sin filtrado, incluye todo lo reciente
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperDT:
    def __init__(self):
        self.base_url = "https://www.dt.gob.cl"
        self.url_legislacion = "https://www.dt.gob.cl/legislacion/1624/w3-channel.html"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def obtener_documentos_dt(self):
        """
        Obtiene los últimos dictámenes y ordinarios publicados
        """
        try:
            logger.info("Obteniendo documentos de la Dirección del Trabajo...")
            
            response = requests.get(self.url_legislacion, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            documentos = []
            
            # Buscar todos los elementos que contengan ORD.N°
            elementos_ord = soup.find_all(string=re.compile(r'ORD\.?\s*N[°º]\s*\d+/\d+', re.IGNORECASE))
            
            # Procesar cada elemento encontrado
            for elemento in elementos_ord[:8]:  # Limitar a 8 documentos máximo
                try:
                    # Extraer el número
                    numero_match = re.search(r'ORD\.?\s*N[°º]\s*\d+/\d+', str(elemento), re.IGNORECASE)
                    if not numero_match:
                        continue
                    numero = numero_match.group()
                    
                    # Obtener el contexto (elemento padre)
                    parent = elemento.parent
                    contador = 0
                    while parent and contador < 5:
                        if parent.name in ['li', 'article', 'div', 'p', 'td']:
                            break
                        parent = parent.parent
                        contador += 1
                    
                    if not parent:
                        parent = elemento.parent
                    
                    # Extraer el texto completo del contexto
                    texto_completo = parent.get_text(separator=' ', strip=True) if parent else str(elemento)
                    
                    # Limpiar y extraer descripción
                    descripcion = texto_completo.replace(numero, '').strip()
                    
                    # Buscar fecha en el texto
                    fecha_str = ""
                    fecha_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', texto_completo)
                    if fecha_match:
                        fecha_str = fecha_match.group()
                    
                    # Si no hay fecha, intentar extraer del número (formato ORD.N°XXX/YY donde YY es el año)
                    if not fecha_str:
                        year_match = re.search(r'/(\d{2})$', numero)
                        if year_match:
                            year = year_match.group(1)
                            # Asumir año 2000+
                            fecha_str = f"20{year}"
                    
                    # Determinar tipo basado en contexto o posición
                    tipo = "Dictamen"
                    if 'ordinario' in texto_completo.lower():
                        tipo = "Ordinario"
                    
                    # Limitar longitud de descripción
                    if len(descripcion) > 150:
                        descripcion = descripcion[:147] + "..."
                    
                    # Si no hay descripción, usar un texto genérico
                    if not descripcion or len(descripcion) < 10:
                        descripcion = f"Documento {numero} de la Dirección del Trabajo"
                    
                    # Buscar URL si existe
                    url = self.url_legislacion
                    if parent:
                        link = parent.find('a', href=True)
                        if link:
                            url = link['href']
                            if not url.startswith('http'):
                                url = self.base_url + url
                    
                    # Agregar documento si no está duplicado
                    if not any(d['numero'] == numero for d in documentos):
                        documentos.append({
                            'tipo': tipo,
                            'numero': numero,
                            'descripcion': descripcion,
                            'fecha': fecha_str,
                            'url': url
                        })
                    
                except Exception as e:
                    logger.debug(f"Error procesando elemento: {e}")
                    continue
            
            # Si encontramos documentos, separarlos mejor por tipo
            if documentos:
                # Intentar clasificar mejor basándose en patrones
                for doc in documentos:
                    # Los primeros 4 suelen ser dictámenes, los siguientes ordinarios
                    if documentos.index(doc) < 4:
                        doc['tipo'] = 'Dictamen'
                    else:
                        doc['tipo'] = 'Ordinario'
            
            logger.info(f"Total documentos DT encontrados: {len(documentos)}")
            return documentos
            
        except Exception as e:
            logger.error(f"Error obteniendo documentos DT: {str(e)}")
            return []


def main():
    """Función principal para pruebas"""
    scraper = ScraperDT()
    documentos = scraper.obtener_documentos_dt()
    
    print("\n" + "="*60)
    print("DOCUMENTOS DE LA DIRECCIÓN DEL TRABAJO")
    print("="*60)
    
    if documentos:
        # Separar por tipo
        dictamenes = [d for d in documentos if d['tipo'] == 'Dictamen']
        ordinarios = [d for d in documentos if d['tipo'] == 'Ordinario']
        
        if dictamenes:
            print("\n📋 DICTÁMENES:")
            print("-" * 40)
            for doc in dictamenes:
                print(f"\n• {doc['numero']}")
                print(f"  {doc['descripcion'][:100]}...")
                if doc['fecha']:
                    print(f"  Fecha: {doc['fecha']}")
        
        if ordinarios:
            print("\n📄 ORDINARIOS:")
            print("-" * 40)
            for doc in ordinarios:
                print(f"\n• {doc['numero']}")
                print(f"  {doc['descripcion'][:100]}...")
                if doc['fecha']:
                    print(f"  Fecha: {doc['fecha']}")
    else:
        print("\n❌ No se encontraron documentos")
    
    print("\n" + "="*60)
    print(f"Total: {len(documentos)} documentos")
    print("="*60)


if __name__ == "__main__":
    main()