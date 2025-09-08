#!/usr/bin/env python3
"""
Scraper para obtener dictámenes y ordinarios de la Dirección del Trabajo del día anterior
Similar al scraper del SII - busca documentos publicados el día anterior
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mapeo de meses en español a números
MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

class ScraperDT:
    def __init__(self):
        self.base_url = "https://www.dt.gob.cl"
        self.url_legislacion = "https://www.dt.gob.cl/legislacion/1624/w3-channel.html"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def convertir_fecha_dt(self, fecha_str):
        """
        Convierte diferentes formatos de fecha a datetime
        """
        try:
            # Formato DD/MM/YYYY o DD-MM-YYYY
            if '/' in fecha_str:
                return datetime.strptime(fecha_str, '%d/%m/%Y')
            elif '-' in fecha_str:
                return datetime.strptime(fecha_str, '%d-%m-%Y')
            # Formato DD de Mes de YYYY
            elif ' de ' in fecha_str.lower():
                fecha_str = fecha_str.lower().strip()
                partes = fecha_str.split(' de ')
                if len(partes) == 3:
                    dia = int(partes[0])
                    mes_str = partes[1]
                    anio = int(partes[2])
                    mes = MESES_ES.get(mes_str)
                    if mes:
                        return datetime(anio, mes, dia)
            return None
        except:
            return None
    
    def obtener_documentos_dt(self, fecha_especifica=None):
        """
        Obtiene los documentos de la DT publicados el día anterior
        
        Args:
            fecha_especifica: Fecha del informe (se buscarán documentos del día anterior)
        """
        try:
            # Calcular fecha del día anterior
            if fecha_especifica:
                if isinstance(fecha_especifica, str):
                    try:
                        fecha_informe = datetime.strptime(fecha_especifica, '%d-%m-%Y')
                    except:
                        fecha_informe = datetime.strptime(fecha_especifica, '%Y-%m-%d')
                else:
                    fecha_informe = fecha_especifica
            else:
                fecha_informe = datetime.now()
            
            fecha_busqueda = fecha_informe - timedelta(days=1)
            logger.info(f"Buscando documentos DT del día anterior ({fecha_busqueda.strftime('%d/%m/%Y')})...")
            
            response = requests.get(self.url_legislacion, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            documentos = []
            documentos_del_dia = []
            
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
            
            # Procesar cada elemento encontrado
            for elemento in elementos_encontrados[:50]:
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
                    
                    # Buscar fecha en el texto
                    fecha_doc = ""
                    fecha_doc_obj = None
                    fecha_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', texto_completo)
                    if fecha_match:
                        fecha_doc = fecha_match.group()
                        fecha_doc_obj = self.convertir_fecha_dt(fecha_doc)
                        # Eliminar la fecha de la descripción
                        descripcion = descripcion.replace(fecha_doc, '')
                    
                    # Verificar si es del día que buscamos
                    es_del_dia = False
                    if fecha_doc_obj:
                        # Comparar solo fecha (sin hora)
                        if fecha_doc_obj.date() == fecha_busqueda.date():
                            es_del_dia = True
                    
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
                    
                    # Crear documento
                    documento = {
                        'tipo': tipo,
                        'numero': numero,
                        'descripcion': descripcion,
                        'fecha': fecha_doc if fecha_doc else "Sin fecha",
                        'url': url
                    }
                    
                    # Agregar documento si no está duplicado
                    if not any(d['numero'] == numero for d in documentos):
                        if es_del_dia:
                            documentos_del_dia.append(documento)
                        else:
                            documentos.append(documento)
                    
                except Exception as e:
                    logger.debug(f"Error procesando elemento: {e}")
                    continue
            
            # Solo retornar documentos del día anterior
            if documentos_del_dia:
                logger.info(f"Documentos DT del {fecha_busqueda.strftime('%d/%m/%Y')}: {len(documentos_del_dia)}")
                return documentos_del_dia[:5]  # Máximo 5 documentos
            
            # Si no hay documentos del día anterior, retornar lista vacía
            logger.info(f"No se encontraron documentos DT del {fecha_busqueda.strftime('%d/%m/%Y')}")
            return []
            
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
    
    # Calcular fecha del día anterior para mostrar
    try:
        fecha_informe = datetime.strptime(fecha, '%d-%m-%Y')
    except:
        fecha_informe = datetime.now()
    fecha_busqueda = fecha_informe - timedelta(days=1)
    
    print("\n" + "="*60)
    print(f"DOCUMENTOS DE LA DIRECCIÓN DEL TRABAJO")
    print(f"Buscando documentos del: {fecha_busqueda.strftime('%d/%m/%Y')}")
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