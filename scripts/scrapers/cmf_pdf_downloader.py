#!/usr/bin/env python3
"""
Descargador especializado para PDFs de CMF con manejo de sesiones y tokens
"""
import requests
import urllib.request
import urllib.parse
import ssl
import logging
from io import BytesIO
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class CMFPDFDownloader:
    """Descargador robusto para PDFs de CMF con múltiples estrategias"""
    
    def __init__(self):
        self.session = None
        self.setup_session()
    
    def setup_session(self):
        """Configura una sesión con headers apropiados para CMF"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
        # Deshabilitar verificación SSL para CMF
        self.session.verify = False
        
        # Suprimir warnings de SSL
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def download_pdf(self, url: str, max_retries: int = 3) -> Tuple[Optional[bytes], str]:
        """
        Descarga un PDF de CMF usando múltiples estrategias
        
        Returns:
            Tuple de (contenido_pdf, método_usado)
        """
        logger.info(f"Intentando descargar PDF de CMF: {url[:80]}...")
        
        # Estrategia 1: Descarga directa con requests y sesión establecida
        for attempt in range(max_retries):
            pdf_content = self._download_with_session(url)
            if pdf_content:
                return pdf_content, "session"
            
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # Espera incremental
        
        # Estrategia 2: urllib con manejo especial de SSL
        pdf_content = self._download_with_urllib(url)
        if pdf_content:
            return pdf_content, "urllib"
        
        # Estrategia 3: Descarga con cookies específicas de CMF
        pdf_content = self._download_with_cookies(url)
        if pdf_content:
            return pdf_content, "cookies"
        
        # Estrategia 4: Descarga directa sin verificación
        pdf_content = self._download_raw(url)
        if pdf_content:
            return pdf_content, "raw"
        
        logger.error(f"No se pudo descargar el PDF después de todos los intentos")
        return None, "failed"
    
    def _download_with_session(self, url: str) -> Optional[bytes]:
        """Descarga usando sesión de requests con cookies"""
        try:
            # Primero establecer sesión visitando el sitio principal
            logger.debug("Estableciendo sesión con CMF...")
            self.session.get('https://www.cmfchile.cl/', timeout=10)
            
            # Agregar referer específico
            headers = {
                'Referer': 'https://www.cmfchile.cl/institucional/mercados/entidad.php',
            }
            
            # Intentar descargar el PDF
            logger.debug("Descargando PDF con sesión establecida...")
            response = self.session.get(
                url, 
                headers=headers,
                timeout=60,
                allow_redirects=True,
                stream=True
            )
            
            if response.status_code == 200:
                content = response.content
                
                # Verificar si es PDF real
                if self._is_pdf(content):
                    logger.info(f"✅ PDF descargado con sesión: {len(content)} bytes")
                    return content
                elif b'<html' in content[:1000].lower():
                    logger.warning("Respuesta es HTML, no PDF")
                else:
                    logger.warning(f"Contenido no reconocido. Primeros bytes: {content[:20]}")
            else:
                logger.warning(f"Status code: {response.status_code}")
                
        except Exception as e:
            logger.debug(f"Error con sesión: {e}")
        
        return None
    
    def _download_with_urllib(self, url: str) -> Optional[bytes]:
        """Descarga usando urllib con manejo especial de SSL"""
        try:
            logger.debug("Intentando con urllib...")
            
            # Crear contexto SSL sin verificación
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Configurar request con headers
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/pdf,*/*')
            req.add_header('Referer', 'https://www.cmfchile.cl/')
            
            # Descargar
            with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
                content = response.read()
                
                if self._is_pdf(content):
                    logger.info(f"✅ PDF descargado con urllib: {len(content)} bytes")
                    return content
                    
        except Exception as e:
            logger.debug(f"Error con urllib: {e}")
        
        return None
    
    def _download_with_cookies(self, url: str) -> Optional[bytes]:
        """Descarga con cookies específicas de CMF"""
        try:
            logger.debug("Intentando con cookies específicas...")
            
            # Parsear la URL para extraer parámetros
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Crear cookies basadas en los parámetros
            cookies = {
                'PHPSESSID': 'cmf_session_' + str(int(time.time())),
            }
            
            # Si hay un parámetro 's567', usarlo como parte de la cookie
            if 's567' in params:
                cookies['cmf_token'] = params['s567'][0]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; CMF Scraper)',
                'Accept': 'application/pdf',
                'Referer': 'https://www.cmfchile.cl/institucional/hechos/hechos.php',
            }
            
            response = requests.get(
                url,
                headers=headers,
                cookies=cookies,
                timeout=60,
                verify=False,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                content = response.content
                if self._is_pdf(content):
                    logger.info(f"✅ PDF descargado con cookies: {len(content)} bytes")
                    return content
                    
        except Exception as e:
            logger.debug(f"Error con cookies: {e}")
        
        return None
    
    def _download_raw(self, url: str) -> Optional[bytes]:
        """Descarga directa sin verificación de certificados"""
        try:
            logger.debug("Intentando descarga directa...")
            
            response = requests.get(
                url,
                timeout=60,
                verify=False,
                allow_redirects=True,
                headers={'User-Agent': 'CMF PDF Downloader'}
            )
            
            if response.status_code == 200:
                content = response.content
                if self._is_pdf(content):
                    logger.info(f"✅ PDF descargado directamente: {len(content)} bytes")
                    return content
                    
        except Exception as e:
            logger.debug(f"Error en descarga directa: {e}")
        
        return None
    
    def _is_pdf(self, content: bytes) -> bool:
        """Verifica si el contenido es un PDF válido"""
        if not content or len(content) < 100:
            return False
        
        # Verificar header de PDF
        if content[:4] == b'%PDF':
            return True
        
        # A veces el PDF puede tener algunos bytes antes del header
        if b'%PDF' in content[:1024]:
            return True
        
        return False
    
    def extract_from_html(self, html_content: str) -> Optional[str]:
        """Extrae información relevante si CMF devuelve HTML en lugar de PDF"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar contenido en diferentes posibles contenedores
            containers = [
                soup.find('div', {'class': 'contenido'}),
                soup.find('div', {'id': 'contenido'}),
                soup.find('div', {'class': 'content'}),
                soup.find('div', {'class': 'documento'}),
                soup.find('main'),
                soup.find('article')
            ]
            
            for container in containers:
                if container:
                    text = container.get_text(strip=True, separator=' ')
                    if len(text) > 100:
                        logger.info(f"✅ Texto extraído del HTML: {len(text)} caracteres")
                        return text
            
            # Si no encontramos contenedores específicos, buscar párrafos
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                if len(text) > 100:
                    logger.info(f"✅ Texto extraído de párrafos HTML: {len(text)} caracteres")
                    return text
                    
        except Exception as e:
            logger.error(f"Error extrayendo de HTML: {e}")
        
        return None
    
    def get_alternative_urls(self, original_url: str) -> list:
        """Genera URLs alternativas para intentar descargar el PDF"""
        alternatives = []
        
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(original_url)
            params = parse_qs(parsed.query)
            
            # Si tiene parámetro s567 (token), intentar variaciones
            if 's567' in params:
                token = params['s567'][0]
                
                # Variación 1: URL directa al archivo
                alternatives.append(
                    f"https://www.cmfchile.cl/sitio/aplic/serdoc/ver_archivo.php?id={token}"
                )
                
                # Variación 2: URL con diferentes parámetros
                alternatives.append(
                    f"https://www.cmfchile.cl/sitio/aplic/serdoc/ver_sgd.php?s567={token}&secuencia=0"
                )
                
                # Variación 3: URL de descarga directa
                alternatives.append(
                    f"https://www.cmfchile.cl/sitio/aplic/serdoc/download.php?id={token}"
                )
                
        except Exception as e:
            logger.debug(f"Error generando URLs alternativas: {e}")
        
        return alternatives


# Instancia global
cmf_pdf_downloader = CMFPDFDownloader()