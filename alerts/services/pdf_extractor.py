"""
Servicio mejorado para extracción de texto de PDFs con múltiples métodos de fallback
"""
import logging
from io import BytesIO
from typing import Tuple, Optional
import PyPDF2
from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import requests

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extractor robusto de texto de PDFs con múltiples métodos de fallback"""
    
    def __init__(self):
        self.methods_priority = [
            ('pypdf2', self._extract_with_pypdf2),
            ('pdfminer', self._extract_with_pdfminer),
            ('pypdf_fallback', self._extract_with_pypdf_fallback),
            ('force_text', self._extract_force_text),
            ('ocr', self._extract_with_ocr),
            ('ocr_enhanced', self._extract_with_enhanced_ocr)
        ]
    
    def extract_text(self, pdf_content: bytes, max_pages: int = 2) -> Tuple[str, str]:
        """
        Extrae texto de un PDF usando múltiples métodos con fallback automático.
        
        Args:
            pdf_content: Contenido del PDF en bytes
            max_pages: Número máximo de páginas a procesar
            
        Returns:
            Tupla (texto_extraido, metodo_usado)
        """
        for method_name, method_func in self.methods_priority:
            try:
                logger.info(f"Intentando extracción con método: {method_name}")
                text = method_func(pdf_content, max_pages)
                
                # Validar que el texto extraído sea útil
                if self._is_valid_text(text):
                    logger.info(f"Extracción exitosa con método: {method_name}")
                    return text, method_name
                else:
                    logger.warning(f"Texto extraído con {method_name} no es válido, intentando siguiente método")
                    
            except Exception as e:
                logger.warning(f"Error con método {method_name}: {str(e)}")
                continue
        
        logger.error("Todos los métodos de extracción fallaron")
        return "", "failed"
    
    def _is_valid_text(self, text: str, min_length: int = 20, min_word_count: int = 3) -> bool:
        """Valida si el texto extraído es útil - MUY leniente para CMF"""
        if not text or len(text.strip()) < min_length:
            return False
        
        # Contar palabras reales (no solo caracteres)
        words = text.split()
        if len(words) < min_word_count:
            return False
        
        # Verificar que no sea solo basura - MUY leniente
        # Aceptar cualquier texto que tenga al menos 30% de caracteres legibles
        alphanumeric_ratio = sum(c.isalnum() or c.isspace() or c in '.,;:-()[]{}/@#$%&*+=|<>"\'' for c in text) / len(text)
        if alphanumeric_ratio < 0.3:  # MUY leniente
            return False
        
        return True
    
    def _extract_with_pypdf2(self, pdf_content: bytes, max_pages: int) -> str:
        """Extrae texto usando PyPDF2"""
        text = ""
        with BytesIO(pdf_content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            num_pages = min(len(reader.pages), max_pages)
            
            for i in range(num_pages):
                page = reader.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip()
    
    def _extract_with_pdfminer(self, pdf_content: bytes, max_pages: int) -> str:
        """Extrae texto usando PDFMiner"""
        with BytesIO(pdf_content) as pdf_file:
            text = extract_text(pdf_file, maxpages=max_pages)
        return text.strip()
    
    def _extract_with_ocr(self, pdf_content: bytes, max_pages: int) -> str:
        """Extrae texto usando OCR básico"""
        text = ""
        images = convert_from_bytes(pdf_content, first_page=1, last_page=max_pages, dpi=200)
        
        for i, image in enumerate(images):
            logger.info(f"Procesando página {i+1} con OCR")
            page_text = pytesseract.image_to_string(image, lang='spa')
            text += page_text + "\n"
        
        return text.strip()
    
    def _extract_with_pypdf_fallback(self, pdf_content: bytes, max_pages: int) -> str:
        """Extrae texto usando pypdf (alternativa a PyPDF2)"""
        try:
            import pypdf
            text = ""
            with BytesIO(pdf_content) as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                num_pages = min(len(reader.pages), max_pages)
                
                for i in range(num_pages):
                    page = reader.pages[i]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return text.strip()
        except:
            return ""
    
    def _extract_force_text(self, pdf_content: bytes, max_pages: int) -> str:
        """Extracción forzada buscando cualquier texto legible en el PDF"""
        try:
            # Decodificar el PDF buscando texto
            pdf_str = pdf_content.decode('latin-1', errors='ignore')
            
            # Buscar patrones de texto entre delimitadores de PDF
            import re
            # Buscar texto entre paréntesis (formato común en PDFs)
            matches = re.findall(r'\((.*?)\)', pdf_str)
            text = ' '.join(matches)
            
            # También buscar secuencias de caracteres imprimibles
            if len(text) < 100:
                ascii_matches = re.findall(r'[\x20-\x7E]{20,}', pdf_str)
                text += ' '.join(ascii_matches)
            
            # Limpiar el texto
            text = re.sub(r'[^\x20-\x7E\n\r\t]+', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()[:10000]  # Limitar a 10k caracteres
        except:
            return ""
    
    def _extract_with_enhanced_ocr(self, pdf_content: bytes, max_pages: int) -> str:
        """Extrae texto usando OCR mejorado con preprocesamiento de imagen"""
        text = ""
        images = convert_from_bytes(pdf_content, first_page=1, last_page=max_pages, dpi=300)
        
        for i, image in enumerate(images):
            logger.info(f"Procesando página {i+1} con OCR mejorado")
            
            # Preprocesar imagen para mejorar OCR
            processed_image = self._preprocess_image_for_ocr(image)
            
            # Configuración mejorada de Tesseract
            custom_config = r'--oem 3 --psm 6'
            page_text = pytesseract.image_to_string(
                processed_image, 
                lang='spa', 
                config=custom_config
            )
            
            text += page_text + "\n"
        
        return text.strip()
    
    def _preprocess_image_for_ocr(self, image: Image) -> Image:
        """Preprocesa una imagen para mejorar la calidad del OCR"""
        import cv2
        import numpy as np
        
        # Convertir PIL Image a numpy array
        img_array = np.array(image)
        
        # Convertir a escala de grises si es necesario
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Aplicar threshold para mejorar contraste
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Eliminar ruido
        denoised = cv2.medianBlur(thresh, 3)
        
        # Convertir de vuelta a PIL Image
        return Image.fromarray(denoised)
    
    def extract_text_from_url(self, url: str, max_pages: int = 2) -> Tuple[str, str]:
        """
        Descarga y extrae texto de un PDF desde una URL.
        
        Args:
            url: URL del PDF
            max_pages: Número máximo de páginas a procesar
            
        Returns:
            Tupla (texto_extraido, metodo_usado)
        """
        try:
            # Asegurar URL completa
            if not url.startswith('http'):
                url = f"https://www.diariooficial.interior.gob.cl{url}"
            
            # Descargar PDF
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Extraer texto
            return self.extract_text(response.content, max_pages)
            
        except Exception as e:
            logger.error(f"Error descargando PDF desde {url}: {str(e)}")
            return "", "failed"
    
    def get_pdf_info(self, pdf_content: bytes) -> dict:
        """Obtiene información básica del PDF"""
        info = {
            'num_pages': 0,
            'size_bytes': len(pdf_content),
            'encrypted': False,
            'has_text': False
        }
        
        try:
            with BytesIO(pdf_content) as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                info['num_pages'] = len(reader.pages)
                info['encrypted'] = reader.is_encrypted
                
                # Verificar si tiene texto extraíble
                if not info['encrypted'] and info['num_pages'] > 0:
                    first_page_text = reader.pages[0].extract_text()
                    info['has_text'] = bool(first_page_text and first_page_text.strip())
                    
        except Exception as e:
            logger.warning(f"Error obteniendo información del PDF: {str(e)}")
        
        return info


# Instancia global del extractor
pdf_extractor = PDFExtractor()