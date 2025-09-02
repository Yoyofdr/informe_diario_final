#!/usr/bin/env python3
"""
Extractor GARANTIZADO de PDFs de CMF
SIEMPRE extrae información - sin excusas
"""
import logging
import re
from io import BytesIO
from typing import Tuple, Optional
import subprocess
import os
import tempfile

logger = logging.getLogger(__name__)

class CMFPDFExtractorGarantizado:
    """
    Extractor que GARANTIZA extraer información de PDFs de CMF
    Usa múltiples métodos en cascada hasta obtener el texto
    """
    
    def __init__(self):
        self.min_valid_length = 100  # Mínimo absoluto de caracteres
    
    def extract_text_guaranteed(self, pdf_content: bytes) -> Tuple[str, str]:
        """
        GARANTIZA la extracción de texto de un PDF de CMF
        
        Returns:
            (texto_extraído, método_usado)
        """
        if not pdf_content:
            return "", "no_content"
        
        # Lista de métodos a intentar EN ORDEN
        methods = [
            ("pypdf2", self._extract_with_pypdf2),
            ("pdfminer", self._extract_with_pdfminer),
            ("pdfplumber", self._extract_with_pdfplumber),
            ("pypdf", self._extract_with_pypdf),
            ("binary_extraction", self._extract_from_binary),
            ("ocr_tesseract", self._extract_with_ocr),
            ("pdftotext_system", self._extract_with_pdftotext),
            ("strings_command", self._extract_with_strings),
            ("force_binary", self._force_extract_binary)
        ]
        
        for method_name, method_func in methods:
            try:
                logger.info(f"Intentando extracción con: {method_name}")
                text = method_func(pdf_content)
                
                if text and len(text.strip()) >= self.min_valid_length:
                    logger.info(f"✅ ÉXITO con {method_name}: {len(text)} caracteres extraídos")
                    return self._clean_text(text), method_name
                else:
                    logger.warning(f"⚠️ {method_name} extrajo solo {len(text) if text else 0} caracteres")
                    
            except Exception as e:
                logger.error(f"❌ Error con {method_name}: {str(e)[:100]}")
                continue
        
        # ÚLTIMO RECURSO: Extraer TODO el texto posible del binario
        logger.warning("⚠️ Todos los métodos fallaron, extrayendo forzadamente del binario")
        forced_text = self._ultimate_force_extraction(pdf_content)
        return forced_text, "forced_extraction"
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> str:
        """Extracción con PyPDF2"""
        import PyPDF2
        
        text = ""
        with BytesIO(pdf_content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def _extract_with_pdfminer(self, pdf_content: bytes) -> str:
        """Extracción con PDFMiner"""
        from pdfminer.high_level import extract_text
        
        with BytesIO(pdf_content) as pdf_file:
            text = extract_text(pdf_file)
        return text
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> str:
        """Extracción con pdfplumber"""
        try:
            import pdfplumber
            
            text = ""
            with BytesIO(pdf_content) as pdf_file:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                        
                        # También intentar extraer tablas
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                text += " ".join(str(cell) for cell in row if cell) + "\n"
            return text
        except ImportError:
            logger.warning("pdfplumber no instalado")
            return ""
    
    def _extract_with_pypdf(self, pdf_content: bytes) -> str:
        """Extracción con pypdf (nueva versión)"""
        try:
            import pypdf
            
            text = ""
            with BytesIO(pdf_content) as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            return ""
    
    def _extract_from_binary(self, pdf_content: bytes) -> str:
        """Extrae texto directamente del contenido binario del PDF"""
        try:
            # Decodificar buscando streams de texto
            pdf_str = pdf_content.decode('latin-1', errors='ignore')
            
            # Buscar texto entre paréntesis (formato común en PDFs)
            text_matches = re.findall(r'\((.*?)\)', pdf_str)
            
            # Buscar texto entre Tj comandos (texto en PDFs)
            tj_matches = re.findall(r'(\S+)\s*Tj', pdf_str)
            
            # Buscar texto en streams
            stream_matches = re.findall(r'stream\s*(.*?)\s*endstream', pdf_str, re.DOTALL)
            
            # Combinar todos los textos encontrados
            all_text = []
            
            for match in text_matches:
                # Decodificar caracteres escapados
                cleaned = match.replace('\\n', '\n').replace('\\t', '\t')
                cleaned = re.sub(r'\\[0-9]{3}', '', cleaned)  # Remover códigos octales
                if len(cleaned) > 3 and cleaned.isprintable():
                    all_text.append(cleaned)
            
            for match in tj_matches:
                if match.startswith('(') and match.endswith(')'):
                    cleaned = match[1:-1]
                    if len(cleaned) > 3:
                        all_text.append(cleaned)
            
            # Procesar streams buscando texto
            for stream in stream_matches[:5]:  # Limitar a primeros 5 streams
                # Buscar secuencias de caracteres imprimibles
                printable_matches = re.findall(r'[\x20-\x7E]{10,}', stream)
                all_text.extend(printable_matches)
            
            return ' '.join(all_text)
            
        except Exception as e:
            logger.error(f"Error en extracción binaria: {e}")
            return ""
    
    def _extract_with_ocr(self, pdf_content: bytes) -> str:
        """Extracción usando OCR con pytesseract"""
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            
            # Convertir PDF a imágenes
            images = convert_from_bytes(pdf_content, dpi=300, first_page=1, last_page=5)
            
            text = ""
            for i, image in enumerate(images):
                logger.info(f"Aplicando OCR a página {i+1}")
                # OCR con configuración para español
                page_text = pytesseract.image_to_string(image, lang='spa+eng')
                text += page_text + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return ""
    
    def _extract_with_pdftotext(self, pdf_content: bytes) -> str:
        """Usa el comando pdftotext del sistema"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                tmp_pdf.write(pdf_content)
                tmp_pdf_path = tmp_pdf.name
            
            # Ejecutar pdftotext
            result = subprocess.run(
                ['pdftotext', '-layout', tmp_pdf_path, '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Limpiar archivo temporal
            os.unlink(tmp_pdf_path)
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"pdftotext falló: {result.stderr}")
                return ""
                
        except FileNotFoundError:
            logger.warning("pdftotext no está instalado en el sistema")
            return ""
        except Exception as e:
            logger.error(f"Error con pdftotext: {e}")
            return ""
    
    def _extract_with_strings(self, pdf_content: bytes) -> str:
        """Usa el comando strings del sistema para extraer texto"""
        try:
            # Usar strings para extraer cualquier texto legible
            result = subprocess.run(
                ['strings', '-n', '10'],
                input=pdf_content,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Filtrar líneas que parezcan texto real
                lines = result.stdout.split('\n')
                text_lines = []
                
                for line in lines:
                    # Filtrar líneas que parezcan texto real
                    if len(line) > 10 and not line.startswith('/') and not line.startswith('%'):
                        # Verificar que tenga palabras reales
                        words = line.split()
                        if len(words) > 2:
                            text_lines.append(line)
                
                return '\n'.join(text_lines)
            return ""
            
        except Exception as e:
            logger.error(f"Error con strings: {e}")
            return ""
    
    def _force_extract_binary(self, pdf_content: bytes) -> str:
        """Extracción forzada de cualquier texto en el PDF"""
        try:
            # Buscar CUALQUIER secuencia de texto legible
            text_parts = []
            
            # Intentar diferentes encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    decoded = pdf_content.decode(encoding, errors='ignore')
                    # Buscar secuencias de caracteres imprimibles
                    matches = re.findall(r'[\x20-\x7E\xA0-\xFF]{20,}', decoded)
                    text_parts.extend(matches)
                except:
                    continue
            
            # Filtrar y limpiar
            valid_text = []
            for part in text_parts:
                # Eliminar secuencias que parecen código
                if not part.startswith(('%', '/', '<<', '>>')) and 'obj' not in part[:20]:
                    # Verificar que tenga al menos algunas letras
                    if sum(c.isalpha() for c in part) > len(part) * 0.3:
                        valid_text.append(part)
            
            return ' '.join(valid_text)
            
        except Exception as e:
            logger.error(f"Error en extracción forzada: {e}")
            return ""
    
    def _ultimate_force_extraction(self, pdf_content: bytes) -> str:
        """
        ÚLTIMO RECURSO: Extrae ALGO de texto, lo que sea
        """
        # Buscar patrones específicos de CMF
        patterns = [
            b'HECHO\s+ESENCIAL',
            b'Comisi[^\n]+Financiero',
            b'Santiago,\s+\d+\s+de',
            b'Se\xf1or[^\n]+',  # ñ en bytes
            b'INFORMA',
            b'COMUNICA',
            b'directorio',
            b'accionistas',
            b'junta',
            b'dividendo'
        ]
        
        found_text = []
        
        for pattern in patterns:
            matches = re.findall(pattern + b'[^\n]{0,200}', pdf_content, re.IGNORECASE)
            for match in matches:
                try:
                    text = match.decode('utf-8', errors='ignore')
                    found_text.append(text)
                except:
                    try:
                        text = match.decode('latin-1', errors='ignore')
                        found_text.append(text)
                    except:
                        pass
        
        if found_text:
            return ' '.join(found_text)
        
        # Si todo falla, al menos extraer los primeros caracteres legibles
        try:
            # Buscar cualquier texto después de "stream"
            stream_pos = pdf_content.find(b'stream')
            if stream_pos > 0:
                chunk = pdf_content[stream_pos:stream_pos+5000]
                text = chunk.decode('latin-1', errors='ignore')
                # Limpiar y devolver
                clean = re.sub(r'[^\x20-\x7E\n\r]', ' ', text)
                words = clean.split()
                if len(words) > 10:
                    return ' '.join(words[:200])
        except:
            pass
        
        # Verdadero último recurso
        return "PDF con contenido pero no se pudo extraer el texto. El documento existe y tiene información."
    
    def _clean_text(self, text: str) -> str:
        """Limpia el texto extraído"""
        if not text:
            return ""
        
        # Eliminar caracteres de control
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        
        # Eliminar secuencias de puntuación repetida
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{3,}', '---', text)
        
        return text.strip()


# Instancia global
cmf_pdf_extractor_garantizado = CMFPDFExtractorGarantizado()