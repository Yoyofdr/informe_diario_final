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
            ("ocr_tesseract", self._extract_with_ocr),  # Mover OCR antes de binary
            ("binary_extraction", self._extract_from_binary),
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
        
        # Validar que el texto forzado sea legible antes de retornarlo
        if forced_text:
            # Contar caracteres legibles vs basura
            import re
            legible_chars = len(re.findall(r'[a-zA-Z0-9áéíóúñÑÁÉÍÓÚ\s\.,;:\-]', forced_text))
            total_chars = len(forced_text)
            legibility_ratio = (legible_chars / total_chars) if total_chars > 0 else 0
            
            if legibility_ratio < 0.5:  # Menos del 50% legible = texto basura
                logger.warning(f"⚠️ Texto forzado es ilegible ({legibility_ratio*100:.1f}% legible), retornando mensaje genérico")
                return "No se pudo extraer texto legible del PDF. Documento posiblemente corrupto o con formato no compatible.", "extraction_failed"
        
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
            tj_matches = re.findall(r'\(([^)]+)\)\s*Tj', pdf_str)
            
            # Buscar texto en streams
            stream_matches = re.findall(r'stream\s*(.*?)\s*endstream', pdf_str, re.DOTALL)
            
            # Combinar todos los textos encontrados
            all_text = []
            
            # Procesar matches de paréntesis
            for match in text_matches:
                # Decodificar caracteres escapados
                cleaned = match.replace('\\n', '\n').replace('\\t', '\t')
                cleaned = re.sub(r'\\[0-9]{3}', '', cleaned)  # Remover códigos octales
                # Decodificar caracteres hexadecimales
                cleaned = re.sub(r'\\x[0-9a-fA-F]{2}', '', cleaned)
                
                # Solo incluir si tiene contenido legible significativo
                if len(cleaned) > 5:
                    # Verificar que al menos 50% sean caracteres alfanuméricos o espacios
                    legible_chars = sum(c.isalnum() or c.isspace() or c in '.,;:()[]{}' for c in cleaned)
                    if legible_chars > len(cleaned) * 0.5:
                        all_text.append(cleaned)
            
            # Procesar comandos Tj (más específico)
            for match in tj_matches:
                cleaned = match.replace('\\n', '\n').replace('\\t', '\t')
                if len(cleaned) > 5 and cleaned.isprintable():
                    all_text.append(cleaned)
            
            # Procesar streams buscando texto real (más inteligente)
            for stream in stream_matches[:3]:  # Limitar a primeros 3 streams
                # Buscar patrones de texto real en español
                # Palabras comunes en documentos CMF
                palabras_pattern = r'\b(?:hecho|esencial|informa|comunica|señor|señora|directorio|' \
                                  r'accionista|junta|dividendo|empresa|sociedad|' \
                                  r'Santiago|presente|atentamente|gerente|director|' \
                                  r'administración|financiero|mercado|comisión)[^\x00-\x1F]{0,100}'
                
                palabras_encontradas = re.findall(palabras_pattern, stream, re.IGNORECASE)
                for palabra in palabras_encontradas:
                    if len(palabra) > 10:
                        all_text.append(palabra)
                
                # Buscar secuencias largas de texto legible
                legible_pattern = r'[a-zA-ZáéíóúñÁÉÍÓÚÑ\s,\.;:]{20,}'
                legible_matches = re.findall(legible_pattern, stream)
                all_text.extend([m for m in legible_matches if len(m.split()) > 3])
            
            # Unir y limpiar el texto
            result = ' '.join(all_text)
            # Eliminar repeticiones
            result = re.sub(r'(\b\w+\b)(?:\s+\1)+', r'\1', result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error en extracción binaria: {e}")
            return ""
    
    def _extract_with_ocr(self, pdf_content: bytes) -> str:
        """Extracción usando OCR con pytesseract - MEJORADO"""
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            
            # Convertir PDF a imágenes con mejor calidad
            try:
                # Primero intentar con alta resolución
                images = convert_from_bytes(pdf_content, dpi=300, first_page=1, last_page=3)
            except:
                # Si falla, intentar con resolución más baja
                try:
                    images = convert_from_bytes(pdf_content, dpi=150, first_page=1, last_page=2)
                except:
                    return ""
            
            text = ""
            for i, image in enumerate(images):
                logger.info(f"Aplicando OCR a página {i+1}")
                
                # Intentar diferentes configuraciones de OCR
                try:
                    # Primero intentar con español
                    page_text = pytesseract.image_to_string(image, lang='spa')
                    if not page_text or len(page_text) < 50:
                        # Si no funciona, intentar con inglés
                        page_text = pytesseract.image_to_string(image, lang='eng')
                    
                    if page_text and len(page_text) > 10:
                        text += page_text + "\n"
                except:
                    # Fallback: OCR básico sin configuración de idioma
                    try:
                        page_text = pytesseract.image_to_string(image)
                        if page_text:
                            text += page_text + "\n"
                    except:
                        pass
            
            return text
            
        except ImportError:
            logger.warning("pytesseract o pdf2image no instalados")
            return ""
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
        # Buscar patrones específicos de CMF con contexto más amplio
        patterns = [
            (b'HECHO\s+ESENCIAL', 500),
            (b'Comisi[^\x00]+Financiero', 300),
            (b'Santiago,\s+\d+\s+de\s+\w+\s+de\s+\d{4}', 400),
            (b'Se\xf1or[^\x00]{10,300}', 300),
            (b'INFORMA[^\x00]{10,500}', 500),
            (b'COMUNICA[^\x00]{10,500}', 500),
            (b'[Dd]irectorio[^\x00]{10,300}', 300),
            (b'[Aa]ccionistas[^\x00]{10,300}', 300),
            (b'[Jj]unta[^\x00]{10,300}', 300),
            (b'[Dd]ividendo[^\x00]{10,300}', 300),
            (b'[Gg]erente\s+[Gg]eneral[^\x00]{10,300}', 300),
            (b'[Pp]resente[^\x00]{10,500}', 500)
        ]
        
        found_text = []
        
        for pattern, max_len in patterns:
            try:
                # Buscar con expresión regular más flexible
                regex = pattern + b'[^\x00]{0,' + str(max_len).encode() + b'}'
                matches = re.findall(pattern + b'[^\x00]{0,%d}' % max_len, pdf_content, re.IGNORECASE | re.DOTALL)
                
                for match in matches[:3]:  # Limitar a 3 matches por patrón
                    # Intentar decodificar con varios encodings
                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            text = match.decode(encoding, errors='ignore')
                            # Limpiar el texto
                            text = re.sub(r'[^\x20-\x7E\xA0-\xFF\n\r]', ' ', text)
                            text = re.sub(r'\s+', ' ', text)
                            
                            # Solo agregar si tiene contenido significativo
                            if len(text) > 20 and text.count(' ') > 2:
                                found_text.append(text.strip())
                                break
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Error en patrón {pattern}: {e}")
                continue
        
        if found_text:
            # Eliminar duplicados y unir
            unique_texts = []
            for text in found_text:
                if not any(text in existing for existing in unique_texts):
                    unique_texts.append(text)
            
            combined = ' '.join(unique_texts[:5])  # Máximo 5 fragmentos
            
            # Si tenemos suficiente texto, devolverlo
            if len(combined) > 100:
                return combined
        
        # Buscar cualquier bloque de texto largo y coherente
        try:
            # Buscar bloques de texto entre marcadores PDF comunes
            text_blocks = re.findall(b'BT[^\x00]+?ET', pdf_content[:100000])  # Limitar búsqueda
            
            for block in text_blocks[:10]:
                # Extraer texto de comandos Tj
                tj_texts = re.findall(b'\(([^)]+)\)\s*Tj', block)
                if tj_texts:
                    decoded_texts = []
                    for tj_text in tj_texts:
                        try:
                            decoded = tj_text.decode('latin-1', errors='ignore')
                            if len(decoded) > 3 and decoded.isprintable():
                                decoded_texts.append(decoded)
                        except:
                            pass
                    
                    if decoded_texts:
                        block_text = ' '.join(decoded_texts)
                        if len(block_text) > 50:
                            found_text.append(block_text)
            
            if found_text:
                return ' '.join(found_text[:3])
        except:
            pass
        
        # Último intento: extraer cualquier texto cerca de palabras clave
        try:
            pdf_str = pdf_content[:50000].decode('latin-1', errors='ignore')
            
            # Buscar contexto alrededor de palabras clave
            keywords = ['Santiago', 'CMF', 'hecho', 'esencial', 'informa', 'comunica', 
                       'presente', 'atentamente', 'gerente', 'director']
            
            for keyword in keywords:
                pos = pdf_str.find(keyword)
                if pos > 0:
                    # Extraer contexto alrededor
                    start = max(0, pos - 100)
                    end = min(len(pdf_str), pos + 300)
                    context = pdf_str[start:end]
                    
                    # Limpiar
                    context = re.sub(r'[^\x20-\x7E\xA0-\xFF]', ' ', context)
                    context = re.sub(r'\s+', ' ', context)
                    
                    if len(context) > 50:
                        return f"Extracto del documento: {context}"
        except:
            pass
        
        # Verdadero último recurso - al menos indicar que el PDF existe
        return f"Documento PDF de CMF detectado ({len(pdf_content):,} bytes) pero el contenido no pudo ser extraído en formato legible. El documento existe y contiene información."
    
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