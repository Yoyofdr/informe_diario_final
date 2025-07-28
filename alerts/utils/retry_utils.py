"""
Utilidades para manejar reintentos con backoff exponencial
"""
import time
import logging
from functools import wraps
from typing import Tuple, Type, Union, Callable
import random

logger = logging.getLogger(__name__)


def retry_with_backoff(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> Callable:
    """
    Decorador que implementa reintentos con backoff exponencial.
    
    Args:
        exceptions: Excepción o tupla de excepciones a capturar
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        backoff_factor: Factor de multiplicación para el delay
        max_delay: Delay máximo en segundos
        jitter: Si añadir variación aleatoria al delay
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Función {func.__name__} falló después de {max_retries} reintentos. "
                            f"Error final: {str(e)}"
                        )
                        raise
                    
                    # Calcular delay con jitter opcional
                    current_delay = delay
                    if jitter:
                        current_delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Función {func.__name__} falló (intento {attempt + 1}/{max_retries + 1}). "
                        f"Error: {str(e)}. Reintentando en {current_delay:.2f} segundos..."
                    )
                    
                    time.sleep(current_delay)
                    
                    # Incrementar delay para el siguiente intento
                    delay = min(delay * backoff_factor, max_delay)
            
            # Este punto no debería alcanzarse nunca
            raise last_exception
        
        return wrapper
    return decorator


def retry_requests():
    """
    Decorador preconfigurado para reintentar peticiones HTTP
    """
    import requests
    
    return retry_with_backoff(
        exceptions=(
            requests.exceptions.RequestException,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        ),
        max_retries=3,
        initial_delay=2.0,
        backoff_factor=2.0,
        max_delay=30.0,
        jitter=True
    )


def retry_selenium():
    """
    Decorador preconfigurado para reintentar operaciones de Selenium
    """
    from selenium.common.exceptions import (
        WebDriverException,
        TimeoutException,
        NoSuchElementException,
        StaleElementReferenceException
    )
    
    return retry_with_backoff(
        exceptions=(
            WebDriverException,
            TimeoutException,
            NoSuchElementException,
            StaleElementReferenceException,
        ),
        max_retries=3,
        initial_delay=3.0,
        backoff_factor=2.0,
        max_delay=30.0,
        jitter=True
    )


def retry_pdf_extraction():
    """
    Decorador preconfigurado para reintentar extracción de PDFs
    """
    return retry_with_backoff(
        exceptions=(Exception,),
        max_retries=2,
        initial_delay=1.0,
        backoff_factor=2.0,
        max_delay=10.0,
        jitter=False
    )

# Alias para compatibilidad con otros módulos
retry = retry_with_backoff