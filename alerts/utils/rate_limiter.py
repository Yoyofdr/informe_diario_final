"""
Implementación de rate limiting para evitar bloqueos del servidor
"""
import time
import threading
from collections import deque
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter con ventana deslizante para controlar la velocidad de las peticiones.
    """
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Args:
            max_requests: Número máximo de peticiones permitidas
            time_window: Ventana de tiempo en segundos
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def acquire(self, wait: bool = True) -> bool:
        """
        Intenta adquirir un slot para hacer una petición.
        
        Args:
            wait: Si esperar cuando se alcanza el límite
            
        Returns:
            True si se puede proceder, False si no
        """
        with self.lock:
            now = time.time()
            
            # Limpiar peticiones antiguas
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # Verificar si podemos hacer la petición
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            if not wait:
                return False
            
            # Calcular cuánto esperar
            oldest_request = self.requests[0]
            wait_time = oldest_request + self.time_window - now + 0.1
            
            logger.info(f"Rate limit alcanzado. Esperando {wait_time:.2f} segundos...")
            
        # Esperar fuera del lock
        time.sleep(wait_time)
        
        # Reintentar
        return self.acquire(wait=False)
    
    def reset(self):
        """Resetea el rate limiter"""
        with self.lock:
            self.requests.clear()


class DomainRateLimiter:
    """
    Rate limiter que maneja múltiples dominios con límites diferentes.
    """
    
    def __init__(self, default_max_requests: int = 10, default_time_window: int = 60):
        """
        Args:
            default_max_requests: Límite por defecto para dominios no configurados
            default_time_window: Ventana de tiempo por defecto
        """
        self.default_max_requests = default_max_requests
        self.default_time_window = default_time_window
        self.limiters: Dict[str, RateLimiter] = {}
        self.domain_configs = {
            # Configuraciones específicas por dominio
            'diariooficial.interior.gob.cl': (5, 60),  # 5 requests por minuto
            'api.gemini.google.com': (60, 60),  # 60 requests por minuto
            'api.huggingface.co': (30, 60),  # 30 requests por minuto
        }
        self.lock = threading.Lock()
    
    def get_domain_from_url(self, url: str) -> str:
        """Extrae el dominio de una URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def get_limiter(self, domain: str) -> RateLimiter:
        """Obtiene o crea un rate limiter para un dominio"""
        with self.lock:
            if domain not in self.limiters:
                # Usar configuración específica o default
                max_requests, time_window = self.domain_configs.get(
                    domain, 
                    (self.default_max_requests, self.default_time_window)
                )
                self.limiters[domain] = RateLimiter(max_requests, time_window)
                logger.info(f"Creado rate limiter para {domain}: {max_requests} requests/{time_window}s")
            
            return self.limiters[domain]
    
    def acquire_for_url(self, url: str, wait: bool = True) -> bool:
        """
        Adquiere un slot para una URL específica.
        
        Args:
            url: URL a la que se va a hacer la petición
            wait: Si esperar cuando se alcanza el límite
            
        Returns:
            True si se puede proceder, False si no
        """
        domain = self.get_domain_from_url(url)
        limiter = self.get_limiter(domain)
        return limiter.acquire(wait)
    
    def configure_domain(self, domain: str, max_requests: int, time_window: int):
        """
        Configura límites específicos para un dominio.
        
        Args:
            domain: Dominio a configurar
            max_requests: Número máximo de peticiones
            time_window: Ventana de tiempo en segundos
        """
        with self.lock:
            self.domain_configs[domain] = (max_requests, time_window)
            # Si ya existe un limiter para este dominio, recrearlo
            if domain in self.limiters:
                del self.limiters[domain]
                logger.info(f"Reconfigurado rate limiter para {domain}: {max_requests} requests/{time_window}s")


# Instancia global del rate limiter
rate_limiter = DomainRateLimiter()


def rate_limited(func):
    """
    Decorador para aplicar rate limiting a funciones que hacen peticiones HTTP.
    La función debe recibir la URL como primer parámetro o como parámetro 'url'.
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Intentar obtener la URL de los argumentos
        url = None
        if args:
            url = args[0] if isinstance(args[0], str) and args[0].startswith('http') else None
        if not url and 'url' in kwargs:
            url = kwargs['url']
        
        if url:
            # Aplicar rate limiting
            rate_limiter.acquire_for_url(url)
        
        return func(*args, **kwargs)
    
    return wrapper