#!/usr/bin/env python3
"""
Scraper mejorado para obtener dictámenes y ordinarios de la Dirección del Trabajo
Versión que no depende de fechas exactas y toma los documentos más recientes
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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
    
    def obtener_documentos_dt(self, fecha_especifica=None):
        """
        Obtiene los documentos más recientes de la DT
        Toma los primeros 5 documentos que encuentra, sin importar la fecha
        
        Args:
            fecha_especifica: Se mantiene por compatibilidad pero no se usa
        """
        try:
            logger.info(f"Obteniendo documentos más recientes de DT...")
            
            response = requests.get(self.url_legislacion, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            documentos = []
            
            # Buscar todos los elementos que contengan ORD.N° o DICTAMEN
            patrones = [
                r'ORD\.?\s*N[°º]\s*\d+(/\d+)?',
                r'DICTAMEN\s*N[°º]\s*\d+',
                r'DIC\.?\s*N[°º]\s*\d+'
            ]
            
            elementos_encontrados = []
            for patron in patrones:
                elementos = soup.find_all(string=re.compile(patron, re.IGNORECASE))
                elementos_encontrados.extend(elementos)
            
            # Procesar cada elemento encontrado (máximo 10 para encontrar 5 buenos)
            for elemento in elementos_encontrados[:10]:
                try:
                    # Extraer el número
                    numero_match = re.search(r'(ORD\.?\s*N[°º]\s*\d+(/\d+)?|DICTAMEN\s*N[°º]\s*\d+|DIC\.?\s*N[°º]\s*\d+)', 
                                           str(elemento), re.IGNORECASE)
                    if not numero_match:
                        continue
                    numero = numero_match.group()
                    
                    # Obtener el contexto (elemento padre)
                    parent = elemento.parent
                    contador = 0
                    while parent and contador < 5:
                        if parent.name in ['li', 'article', 'div', 'p', 'td', 'tr']:
                            break
                        parent = parent.parent
                        contador += 1
                    
                    if not parent:
                        parent = elemento.parent
                    
                    # Extraer el texto completo del contexto
                    texto_completo = parent.get_text(separator=' ', strip=True) if parent else str(elemento)
                    
                    # Limpiar y extraer descripción
                    # Eliminar el número del texto
                    descripcion = texto_completo
                    for parte in [numero, 'Dictamen destacado']:
                        descripcion = descripcion.replace(parte, '')
                    
                    # Buscar fecha en el texto (aunque puede estar mal)
                    fecha_doc = ""
                    fecha_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', texto_completo)
                    if fecha_match:
                        fecha_doc = fecha_match.group()
                        # Eliminar la fecha de la descripción
                        descripcion = descripcion.replace(fecha_doc, '')
                    
                    # Limpiar descripción
                    descripcion = ' '.join(descripcion.split())
                    descripcion = descripcion.strip(' ;,.')
                    
                    # Determinar tipo basado en el contenido
                    tipo = "Ordinario"  # Por defecto
                    if 'dictamen' in numero.lower() or 'dic.' in numero.lower():
                        tipo = "Dictamen"
                    elif 'ord' in numero.lower():
                        tipo = "Ordinario"
                    
                    # Limitar longitud de descripción
                    if len(descripcion) > 150:
                        descripcion = descripcion[:147] + "..."
                    
                    # Si no hay descripción o es muy corta, usar un texto genérico
                    if not descripcion or len(descripcion) < 10:
                        descripcion = f"Documento laboral de la Dirección del Trabajo"
                    
                    # Buscar URL si existe
                    url = self.url_legislacion
                    if parent:
                        link = parent.find('a', href=True)
                        if link:
                            url = link['href']
                            if not url.startswith('http'):
                                url = self.base_url + url
                    
                    # Limpiar el número (normalizar formato)
                    numero = numero.replace('  ', ' ').strip()
                    
                    # Agregar documento si no está duplicado
                    if not any(d['numero'] == numero for d in documentos):
                        documentos.append({
                            'tipo': tipo,
                            'numero': numero,
                            'descripcion': descripcion,
                            'fecha': fecha_doc if fecha_doc else "Reciente",
                            'url': url
                        })
                    
                    # Si ya tenemos 5 documentos, parar
                    if len(documentos) >= 5:
                        break
                    
                except Exception as e:
                    logger.debug(f"Error procesando elemento: {e}")
                    continue
            
            # Si no encontramos suficientes, intentar buscar en la estructura de la página
            if len(documentos) < 5:
                # Buscar en elementos con clase específica o estructura conocida
                articulos = soup.find_all(['article', 'li'], limit=20)
                for articulo in articulos:
                    texto = articulo.get_text(separator=' ', strip=True)
                    # Buscar patrón de ORD o DICTAMEN
                    if re.search(r'ORD\.?\s*N[°º]\s*\d+|DICTAMEN', texto, re.IGNORECASE):
                        # Procesar similar al anterior
                        numero_match = re.search(r'(ORD\.?\s*N[°º]\s*\d+(/\d+)?|DICTAMEN\s*N[°º]\s*\d+)', texto, re.IGNORECASE)
                        if numero_match and not any(d['numero'] == numero_match.group() for d in documentos):
                            numero = numero_match.group()
                            descripcion = texto.replace(numero, '').strip()
                            
                            # Buscar fecha
                            fecha_doc = ""
                            fecha_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', texto)
                            if fecha_match:
                                fecha_doc = fecha_match.group()
                                descripcion = descripcion.replace(fecha_doc, '')
                            
                            # Limpiar y limitar descripción
                            descripcion = ' '.join(descripcion.split())[:150]
                            if not descripcion:
                                descripcion = "Documento laboral de la DT"
                            
                            documentos.append({
                                'tipo': 'Dictamen' if 'dictamen' in numero.lower() else 'Ordinario',
                                'numero': numero,
                                'descripcion': descripcion,
                                'fecha': fecha_doc if fecha_doc else "Reciente",
                                'url': self.url_legislacion
                            })
                            
                            if len(documentos) >= 5:
                                break
            
            logger.info(f"Total documentos DT encontrados: {len(documentos)}")
            return documentos[:5]  # Máximo 5 documentos
            
        except Exception as e:
            logger.error(f"Error obteniendo documentos DT: {str(e)}")
            return []


def main():
    """Función principal para pruebas"""
    import sys
    
    # Obtener fecha de argumentos o usar hoy
    if len(sys.argv) > 1:
        fecha = sys.argv[1]
    else:
        fecha = datetime.now().strftime('%d-%m-%Y')
    
    scraper = ScraperDT()
    documentos = scraper.obtener_documentos_dt(fecha)
    
    print("\n" + "="*60)
    print(f"DOCUMENTOS DE LA DIRECCIÓN DEL TRABAJO")
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