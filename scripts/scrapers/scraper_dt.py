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
    
    def obtener_documentos_dt(self, fecha_especifica=None):
        """
        Obtiene dictámenes y ordinarios publicados en una fecha específica
        Si no se proporciona fecha, usa la fecha actual
        
        Args:
            fecha_especifica: Fecha en formato 'DD-MM-YYYY' o datetime
        """
        try:
            # Procesar la fecha
            if fecha_especifica:
                if isinstance(fecha_especifica, str):
                    # Convertir string a datetime
                    try:
                        fecha_obj = datetime.strptime(fecha_especifica, '%d-%m-%Y')
                    except:
                        fecha_obj = datetime.strptime(fecha_especifica, '%Y-%m-%d')
                else:
                    fecha_obj = fecha_especifica
            else:
                fecha_obj = datetime.now()
            
            fecha_str = fecha_obj.strftime('%d-%m-%Y')
            # Diferentes formatos para comparación
            fecha_comparacion = fecha_obj.strftime('%d/%m/%Y')
            fecha_comparacion2 = fecha_obj.strftime('%d-%m-%Y')
            fecha_comparacion3 = fecha_obj.strftime('%d.%m.%Y')
            # Sin ceros a la izquierda
            fecha_comparacion4 = fecha_obj.strftime('%-d/%-m/%Y') if hasattr(fecha_obj, 'strftime') else fecha_obj.strftime('%d/%m/%Y').replace('/0', '/')
            fecha_comparacion5 = fecha_obj.strftime('%-d-%-m-%Y') if hasattr(fecha_obj, 'strftime') else fecha_obj.strftime('%d-%m-%Y').replace('-0', '-')
            
            logger.info(f"Obteniendo documentos DT para fecha: {fecha_str}")
            
            response = requests.get(self.url_legislacion, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            documentos = []
            
            # Buscar todos los elementos que contengan ORD.N° o DICTAMEN
            patrones = [
                r'ORD\.?\s*N[°º]\s*\d+/\d+',
                r'DICTAMEN\s*N[°º]\s*\d+',
                r'DIC\.?\s*N[°º]\s*\d+'
            ]
            
            elementos_encontrados = []
            for patron in patrones:
                elementos = soup.find_all(string=re.compile(patron, re.IGNORECASE))
                elementos_encontrados.extend(elementos)
            
            # Procesar cada elemento encontrado
            for elemento in elementos_encontrados[:50]:  # Buscar en más elementos para encontrar los del día
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
                    fecha_doc = ""
                    fecha_encontrada = False
                    
                    # Buscar diferentes formatos de fecha
                    patrones_fecha = [
                        r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
                        r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',
                        r'\d{1,2}\.(\d{1,2})\.\d{4}'
                    ]
                    
                    for patron_fecha in patrones_fecha:
                        fecha_match = re.search(patron_fecha, texto_completo)
                        if fecha_match:
                            fecha_doc = fecha_match.group()
                            # Verificar si coincide con la fecha buscada
                            fechas_comparar = [fecha_comparacion, fecha_comparacion2, fecha_comparacion3, 
                                             fecha_comparacion4, fecha_comparacion5]
                            for fc in fechas_comparar:
                                if fc in fecha_doc or fecha_doc == fc:
                                    fecha_encontrada = True
                                    break
                            if fecha_encontrada:
                                break
                    
                    # Si no encontramos la fecha del día, saltar este documento
                    if not fecha_encontrada:
                        continue
                    
                    # Determinar tipo basado en el contenido
                    tipo = "Ordinario"  # Por defecto
                    if 'dictamen' in numero.lower() or 'dic.' in numero.lower():
                        tipo = "Dictamen"
                    elif 'ord' in numero.lower():
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
                            'fecha': fecha_doc,
                            'url': url
                        })
                    
                except Exception as e:
                    logger.debug(f"Error procesando elemento: {e}")
                    continue
            
            # Limitar a máximo 5 documentos (como en otras secciones)
            documentos = documentos[:5]
            
            logger.info(f"Total documentos DT del {fecha_str}: {len(documentos)}")
            return documentos
            
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
    print(f"DOCUMENTOS DE LA DIRECCIÓN DEL TRABAJO - {fecha}")
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