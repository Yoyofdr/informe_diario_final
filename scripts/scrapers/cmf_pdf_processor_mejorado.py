#!/usr/bin/env python3
"""
Procesador mejorado de PDFs de CMF con mejor manejo de texto extraído
"""
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class CMFPDFProcessor:
    """Procesador especializado para PDFs de CMF"""
    
    def __init__(self):
        self.min_text_length = 50  # Mínimo de caracteres para considerar válido
    
    def clean_extracted_text(self, text: str) -> str:
        """
        Limpia y mejora el texto extraído de PDFs de CMF
        """
        if not text:
            return ""
        
        # Eliminar caracteres de control y espacios excesivos
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalizar saltos de línea
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        # Eliminar espacios múltiples pero mantener saltos de línea
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Limpiar espacios al inicio y final de líneas
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        # Eliminar líneas vacías múltiples
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        return text.strip()
    
    def validate_text_quality(self, text: str) -> Tuple[bool, str]:
        """
        Valida la calidad del texto extraído
        Returns: (es_válido, razón)
        """
        if not text:
            return False, "Texto vacío"
        
        cleaned_text = self.clean_extracted_text(text)
        
        if len(cleaned_text) < self.min_text_length:
            return False, f"Texto muy corto ({len(cleaned_text)} caracteres)"
        
        # Verificar que tiene palabras reales
        words = cleaned_text.split()
        if len(words) < 10:
            return False, f"Pocas palabras ({len(words)})"
        
        # Verificar que no es solo basura
        alphanumeric_ratio = sum(c.isalnum() or c.isspace() for c in cleaned_text) / len(cleaned_text)
        if alphanumeric_ratio < 0.5:
            return False, f"Texto con muchos caracteres especiales ({alphanumeric_ratio:.1%} legible)"
        
        # Verificar que tiene contenido relevante de CMF
        palabras_clave = ['hecho', 'esencial', 'informa', 'comunica', 'señor', 'señora', 
                          'presente', 'santiago', 'directorio', 'accionista', 'junta',
                          'dividendo', 'acuerdo', 'aprobó', 'sociedad', 'empresa']
        
        texto_lower = cleaned_text.lower()
        if not any(palabra in texto_lower for palabra in palabras_clave):
            # Podría ser un PDF válido pero no un hecho esencial típico
            logger.warning("Texto sin palabras clave típicas de hecho esencial")
        
        return True, "Texto válido"
    
    def extract_key_information(self, text: str) -> dict:
        """
        Extrae información clave del texto del hecho esencial
        """
        info = {
            'fecha': None,
            'destinatario': None,
            'remitente': None,
            'asunto_principal': None,
            'montos': [],
            'fechas_importantes': [],
            'nombres_mencionados': []
        }
        
        if not text:
            return info
        
        lines = text.split('\n')
        
        # Buscar fecha del documento
        fecha_pattern = r'\b(\d{1,2})\s*de\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*de\s*(\d{4})\b'
        for line in lines[:20]:  # Buscar en las primeras líneas
            match = re.search(fecha_pattern, line, re.IGNORECASE)
            if match:
                info['fecha'] = match.group(0)
                break
        
        # Buscar destinatario (típicamente "Señor/Señora...")
        for i, line in enumerate(lines[:30]):
            if 'señor' in line.lower() or 'señora' in line.lower():
                info['destinatario'] = line.strip()
                # Las siguientes líneas suelen tener el nombre y cargo
                if i < len(lines) - 2:
                    info['destinatario'] += ' ' + lines[i+1].strip()
                break
        
        # Buscar montos
        monto_pattern = r'\$[\d.,]+|[\d.,]+\s*UF|US\$[\d.,]+|[\d.,]+\s*millones'
        for line in lines:
            montos = re.findall(monto_pattern, line, re.IGNORECASE)
            info['montos'].extend(montos)
        
        # Buscar nombres de personas (palabras capitalizadas consecutivas)
        nombre_pattern = r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}\b'
        for line in lines:
            nombres = re.findall(nombre_pattern, line)
            info['nombres_mencionados'].extend(nombres)
        
        # Deduplicar listas
        info['montos'] = list(set(info['montos']))[:5]  # Máximo 5 montos
        info['nombres_mencionados'] = list(set(info['nombres_mencionados']))[:10]
        
        return info
    
    def process_pdf_text(self, text: str, entidad: str, materia: str) -> Tuple[str, dict]:
        """
        Procesa el texto extraído de un PDF de CMF
        Returns: (texto_limpio, información_extraída)
        """
        # Limpiar el texto
        cleaned_text = self.clean_extracted_text(text)
        
        # Validar calidad
        is_valid, reason = self.validate_text_quality(cleaned_text)
        
        if not is_valid:
            logger.warning(f"Texto de {entidad} no válido: {reason}")
            # Intentar recuperar algo de información
            if len(cleaned_text) > 20:
                # Hay algo de texto, úsalo aunque sea poco
                logger.info(f"Usando texto parcial de {entidad} ({len(cleaned_text)} caracteres)")
            else:
                return "", {}
        
        # Extraer información clave
        key_info = self.extract_key_information(cleaned_text)
        
        # Log de información extraída
        logger.info(f"Información extraída de {entidad}:")
        logger.info(f"  - Fecha documento: {key_info['fecha']}")
        logger.info(f"  - Montos encontrados: {len(key_info['montos'])}")
        logger.info(f"  - Nombres mencionados: {len(key_info['nombres_mencionados'])}")
        
        return cleaned_text, key_info
    
    def generate_fallback_summary(self, entidad: str, materia: str, key_info: dict) -> str:
        """
        Genera un resumen de respaldo cuando no se puede usar IA
        """
        summary_parts = [f"{entidad} comunicó {materia}"]
        
        if key_info.get('fecha'):
            summary_parts.append(f"con fecha {key_info['fecha']}")
        
        if key_info.get('montos'):
            montos_str = ', '.join(key_info['montos'][:3])
            summary_parts.append(f"involucrando montos de {montos_str}")
        
        if key_info.get('nombres_mencionados') and 'cambios' in materia.lower():
            nombres = ', '.join(key_info['nombres_mencionados'][:3])
            summary_parts.append(f"mencionando a {nombres}")
        
        return '. '.join(summary_parts) + '.'


# Instancia global
cmf_pdf_processor = CMFPDFProcessor()