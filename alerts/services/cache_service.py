"""
Servicio de caché para optimizar el scraping del Diario Oficial
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Servicio para gestionar el caché del scraping"""
    
    # Tiempos de expiración en segundos
    PDF_CACHE_TIME = 86400 * 7  # 7 días para PDFs
    SCRAPING_RESULT_CACHE_TIME = 86400  # 24 horas para resultados de scraping
    API_RESPONSE_CACHE_TIME = 3600  # 1 hora para respuestas de API
    
    @staticmethod
    def _generate_key(prefix: str, identifier: str) -> str:
        """Genera una clave única para el caché"""
        return f"{prefix}:{identifier}"
    
    @staticmethod
    def _hash_url(url: str) -> str:
        """Genera un hash MD5 de una URL para usar como clave"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get_pdf_content(self, url: str) -> Optional[bytes]:
        """Obtiene el contenido de un PDF del caché"""
        key = self._generate_key("pdf", self._hash_url(url))
        content = cache.get(key)
        if content:
            logger.info(f"PDF encontrado en caché: {url}")
        return content
    
    def set_pdf_content(self, url: str, content: bytes) -> None:
        """Guarda el contenido de un PDF en el caché"""
        key = self._generate_key("pdf", self._hash_url(url))
        cache.set(key, content, self.PDF_CACHE_TIME)
        logger.info(f"PDF guardado en caché: {url}")
    
    def get_scraping_result(self, date: datetime) -> Optional[Dict[str, Any]]:
        """Obtiene los resultados del scraping para una fecha específica"""
        date_str = date.strftime("%Y-%m-%d")
        key = self._generate_key("scraping", date_str)
        result = cache.get(key)
        if result:
            logger.info(f"Resultados de scraping encontrados en caché para: {date_str}")
        return result
    
    def set_scraping_result(self, date: datetime, results: Dict[str, Any]) -> None:
        """Guarda los resultados del scraping en el caché"""
        date_str = date.strftime("%Y-%m-%d")
        key = self._generate_key("scraping", date_str)
        cache.set(key, results, self.SCRAPING_RESULT_CACHE_TIME)
        logger.info(f"Resultados de scraping guardados en caché para: {date_str}")
    
    def get_api_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Obtiene una respuesta de API del caché"""
        params_str = json.dumps(params, sort_keys=True)
        identifier = f"{endpoint}:{self._hash_url(params_str)}"
        key = self._generate_key("api", identifier)
        response = cache.get(key)
        if response:
            logger.info(f"Respuesta API encontrada en caché: {endpoint}")
        return response
    
    def set_api_response(self, endpoint: str, params: Dict[str, Any], response: Dict[str, Any]) -> None:
        """Guarda una respuesta de API en el caché"""
        params_str = json.dumps(params, sort_keys=True)
        identifier = f"{endpoint}:{self._hash_url(params_str)}"
        key = self._generate_key("api", identifier)
        cache.set(key, response, self.API_RESPONSE_CACHE_TIME)
        logger.info(f"Respuesta API guardada en caché: {endpoint}")
    
    def invalidate_scraping_cache(self, date: datetime) -> None:
        """Invalida el caché de scraping para una fecha específica"""
        date_str = date.strftime("%Y-%m-%d")
        key = self._generate_key("scraping", date_str)
        cache.delete(key)
        logger.info(f"Caché de scraping invalidado para: {date_str}")
    
    def get_or_set(self, key: str, callable_func, timeout: int = None) -> Any:
        """Obtiene un valor del caché o lo genera y guarda si no existe"""
        value = cache.get(key)
        if value is None:
            value = callable_func()
            cache.set(key, value, timeout or self.SCRAPING_RESULT_CACHE_TIME)
        return value
    
    def clear_old_cache(self) -> None:
        """Limpia entradas antiguas del caché (se puede llamar desde una tarea periódica)"""
        # Django Redis maneja la expiración automáticamente,
        # pero podemos implementar lógica adicional si es necesario
        logger.info("Limpieza de caché ejecutada")


# Instancia global del servicio
cache_service = CacheService()