"""
Servicio de caché para OpenAI - Reduce costos evitando llamadas duplicadas
"""
import hashlib
import json
from datetime import datetime, timedelta
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class OpenAICacheService:
    """
    Caché para respuestas de OpenAI
    Evita procesar el mismo documento múltiples veces
    """
    
    CACHE_DURATION = 86400 * 7  # 7 días
    
    @staticmethod
    def get_cache_key(tipo, contenido):
        """Genera una clave única basada en el contenido"""
        content_hash = hashlib.md5(contenido.encode()).hexdigest()
        return f"openai:{tipo}:{content_hash}"
    
    @classmethod
    def get_cached_evaluation(cls, titulo, texto_pdf=None):
        """Obtiene una evaluación cacheada si existe"""
        contenido = f"{titulo}:{texto_pdf[:500] if texto_pdf else ''}"
        key = cls.get_cache_key("eval", contenido)
        result = cache.get(key)
        if result:
            logger.info(f"✅ Evaluación encontrada en caché para: {titulo[:50]}...")
        return result
    
    @classmethod
    def cache_evaluation(cls, titulo, texto_pdf, resultado):
        """Guarda una evaluación en caché"""
        contenido = f"{titulo}:{texto_pdf[:500] if texto_pdf else ''}"
        key = cls.get_cache_key("eval", contenido)
        cache.set(key, resultado, cls.CACHE_DURATION)
        logger.info(f"💾 Evaluación guardada en caché para: {titulo[:50]}...")
    
    @classmethod
    def get_cached_summary(cls, entidad, materia, texto_pdf=None):
        """Obtiene un resumen cacheado si existe"""
        contenido = f"{entidad}:{materia}:{texto_pdf[:500] if texto_pdf else ''}"
        key = cls.get_cache_key("summary", contenido)
        result = cache.get(key)
        if result:
            logger.info(f"✅ Resumen encontrado en caché para: {entidad} - {materia[:30]}...")
        return result
    
    @classmethod
    def cache_summary(cls, entidad, materia, texto_pdf, resumen):
        """Guarda un resumen en caché"""
        contenido = f"{entidad}:{materia}:{texto_pdf[:500] if texto_pdf else ''}"
        key = cls.get_cache_key("summary", contenido)
        cache.set(key, resumen, cls.CACHE_DURATION)
        logger.info(f"💾 Resumen guardado en caché para: {entidad} - {materia[:30]}...")
    
    @classmethod
    def get_stats(cls):
        """Obtiene estadísticas del caché (para monitoreo)"""
        # Esto es aproximado ya que Django cache no da stats directas
        return {
            "tipo": "FileBasedCache",
            "duracion_dias": cls.CACHE_DURATION / 86400,
            "activo": True
        }