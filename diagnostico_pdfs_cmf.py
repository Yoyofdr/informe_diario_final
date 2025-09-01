#!/usr/bin/env python3
"""
Diagnóstico completo del problema con PDFs de CMF
"""

import requests
import json
from datetime import datetime, timedelta
import logging
from io import BytesIO
import PyPDF2
from pdfminer.high_level import extract_text as pdfminer_extract
import sys
sys.path.append('.')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnosticar_pdfs_cmf():
    """Diagnóstico completo del problema"""
    
    print("🔍 DIAGNÓSTICO DE PDFs CMF")
    print("=" * 60)
    
    # 1. Verificar datos CMF disponibles
    try:
        with open('data/hechos_cmf_selenium_reales.json', 'r') as f:
            data = json.load(f)
            print(f"📊 Hechos CMF en archivo: {len(data)}")
            
            if data:
                for i, hecho in enumerate(data[:3]):
                    print(f"\n{i+1}. {hecho.get('entidad', 'Sin entidad')}")
                    url_pdf = hecho.get('url_pdf', '')
                    print(f"   URL: {url_pdf}")
                    
                    if url_pdf:
                        # Intentar descargar
                        print("   🔄 Intentando descargar...")
                        pdf_content = descargar_pdf_debug(url_pdf)
                        
                        if pdf_content:
                            print(f"   ✅ Descargado: {len(pdf_content)} bytes")
                            
                            # Intentar extraer texto
                            texto = extraer_texto_debug(pdf_content)
                            if texto:
                                print(f"   ✅ Texto extraído: {len(texto)} caracteres")
                                print(f"   Preview: {texto[:100]}...")
                            else:
                                print("   ❌ No se pudo extraer texto")
                                # Analizar por qué
                                analizar_pdf(pdf_content)
                        else:
                            print("   ❌ No se pudo descargar")
                            # Probar URL alternativas
                            probar_urls_alternativas(hecho)
    except Exception as e:
        print(f"❌ Error leyendo datos: {e}")

def descargar_pdf_debug(url):
    """Descarga PDF con debugging"""
    try:
        # Método 1: requests simple
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        print(f"      Status: {response.status_code}")
        print(f"      Content-Type: {response.headers.get('content-type', 'Unknown')}")
        
        if response.status_code == 200:
            content = response.content
            if content[:4] == b'%PDF':
                return content
            else:
                print(f"      ⚠️ No es PDF. Primeros bytes: {content[:20]}")
        
        return None
        
    except Exception as e:
        print(f"      Error: {e}")
        return None

def extraer_texto_debug(pdf_content):
    """Extrae texto con debugging"""
    texto = ""
    
    # Método 1: PyPDF2
    try:
        with BytesIO(pdf_content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            print(f"      Páginas: {len(reader.pages)}")
            
            for i in range(min(3, len(reader.pages))):
                page = reader.pages[i]
                page_text = page.extract_text()
                if page_text:
                    texto += page_text
                    
        if texto:
            print(f"      PyPDF2 extrajo: {len(texto)} caracteres")
            return texto
    except Exception as e:
        print(f"      PyPDF2 falló: {e}")
    
    # Método 2: pdfminer
    try:
        with BytesIO(pdf_content) as pdf_file:
            texto = pdfminer_extract(pdf_file)
            
        if texto:
            print(f"      PDFMiner extrajo: {len(texto)} caracteres")
            return texto
    except Exception as e:
        print(f"      PDFMiner falló: {e}")
    
    return ""

def analizar_pdf(pdf_content):
    """Analiza por qué no se puede extraer texto"""
    print("   📋 Análisis del PDF:")
    
    # Verificar si está encriptado
    try:
        with BytesIO(pdf_content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            if reader.is_encrypted:
                print("      ⚠️ PDF está ENCRIPTADO")
            else:
                print("      ✅ PDF no está encriptado")
                
            # Verificar metadata
            meta = reader.metadata
            if meta:
                print(f"      Producer: {meta.get('/Producer', 'Unknown')}")
                print(f"      Creator: {meta.get('/Creator', 'Unknown')}")
    except Exception as e:
        print(f"      Error analizando: {e}")
    
    # Verificar si es imagen escaneada
    if b'/Image' in pdf_content[:5000] or b'/XObject' in pdf_content[:5000]:
        print("      ⚠️ Posible PDF escaneado (contiene imágenes)")
    
    # Verificar encoding
    if b'/Encoding' in pdf_content[:5000]:
        print("      ⚠️ PDF con encoding especial")

def probar_urls_alternativas(hecho):
    """Prueba URLs alternativas para el PDF"""
    print("   🔄 Probando URLs alternativas...")
    
    entidad = hecho.get('entidad', '')
    fecha = hecho.get('fecha_publicacion', '')
    numero = hecho.get('numero_hecho', '')
    
    # Construir URLs alternativas
    urls_alternativas = []
    
    if fecha and numero:
        fecha_sin_barras = fecha.replace('/', '')
        urls_alternativas.append(
            f"https://www.cmfchile.cl/institucional/publicaciones/normativa_pdf/he/2025/he_{fecha_sin_barras}_{numero}.pdf"
        )
        urls_alternativas.append(
            f"https://www.cmfchile.cl/portal/principal/613/articles-{numero}_doc_pdf.pdf"
        )
    
    for url in urls_alternativas:
        print(f"      Probando: {url[:60]}...")
        content = descargar_pdf_debug(url)
        if content:
            print(f"      ✅ Funciona!")
            return url
    
    return None

if __name__ == "__main__":
    diagnosticar_pdfs_cmf()