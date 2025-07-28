"""
Configuración de logging estructurado para el sistema
"""
import logging
import logging.config
import json
from datetime import datetime
from pathlib import Path
import os


class StructuredFormatter(logging.Formatter):
    """Formatter que produce logs en formato JSON estructurado"""
    
    def format(self, record):
        """Formatea el registro en JSON estructurado"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Agregar campos extra si existen
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'exc_info',
                          'exc_text', 'stack_info', 'pathname', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'getMessage']:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(log_level='INFO', log_dir='logs', structured=True):
    """
    Configura el sistema de logging.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directorio donde guardar los logs
        structured: Si usar formato JSON estructurado o formato tradicional
    """
    # Crear directorio de logs si no existe
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Configuración base
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'structured': {
                '()': StructuredFormatter,
            },
            'traditional': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'traditional',
                'stream': 'ext://sys.stdout'
            },
            'file_general': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured' if structured else 'detailed',
                'filename': str(log_path / 'diario_oficial.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8'
            },
            'file_errors': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'structured' if structured else 'detailed',
                'filename': str(log_path / 'errors.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8'
            },
            'file_scraping': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'structured' if structured else 'detailed',
                'filename': str(log_path / 'scraping.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 7,
                'encoding': 'utf-8'
            },
            'file_metrics': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': str(log_path / 'metrics.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            # Logger raíz
            '': {
                'handlers': ['console', 'file_general'],
                'level': log_level,
                'propagate': False
            },
            # Logger específico para scraping
            'alerts.scraper_diario_oficial': {
                'handlers': ['console', 'file_scraping', 'file_errors'],
                'level': 'DEBUG',
                'propagate': False
            },
            # Logger para servicios
            'alerts.services': {
                'handlers': ['console', 'file_general', 'file_errors'],
                'level': 'INFO',
                'propagate': False
            },
            # Logger para métricas
            'alerts.services.metrics_service': {
                'handlers': ['file_metrics'],
                'level': 'INFO',
                'propagate': False
            },
            # Logger para utils
            'alerts.utils': {
                'handlers': ['console', 'file_general'],
                'level': 'INFO',
                'propagate': False
            },
            # Reducir ruido de librerías externas
            'selenium': {
                'handlers': ['file_general'],
                'level': 'WARNING',
                'propagate': False
            },
            'urllib3': {
                'handlers': ['file_general'],
                'level': 'WARNING',
                'propagate': False
            },
            'requests': {
                'handlers': ['file_general'],
                'level': 'WARNING',
                'propagate': False
            }
        }
    }
    
    # Aplicar configuración
    logging.config.dictConfig(config)
    
    # Log inicial
    logger = logging.getLogger(__name__)
    logger.info(
        "Sistema de logging configurado",
        extra={
            'log_level': log_level,
            'log_dir': str(log_path),
            'structured': structured
        }
    )


def get_logger(name, **extra_fields):
    """
    Obtiene un logger con campos extra predefinidos.
    
    Args:
        name: Nombre del logger
        **extra_fields: Campos adicionales para incluir en todos los logs
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Crear un adaptador que agrega campos extra automáticamente
    class ContextAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # Agregar campos extra a cada mensaje
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra'].update(self.extra)
            return msg, kwargs
    
    return ContextAdapter(logger, extra_fields)


# Funciones de utilidad para logging
def log_execution_time(logger, operation_name):
    """
    Context manager para medir y loggear tiempo de ejecución.
    
    Uso:
        with log_execution_time(logger, "scraping_pdf"):
            # código a medir
    """
    import time
    from contextlib import contextmanager
    
    @contextmanager
    def timer():
        start_time = time.time()
        logger.info(f"Iniciando operación: {operation_name}")
        try:
            yield
        finally:
            duration = time.time() - start_time
            logger.info(
                f"Operación completada: {operation_name}",
                extra={'duration_seconds': duration}
            )
    
    return timer()


def log_exception(logger, operation_name):
    """
    Decorador para loggear excepciones con contexto.
    
    Uso:
        @log_exception(logger, "pdf_extraction")
        def extract_pdf():
            # código que puede fallar
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error en operación {operation_name}",
                    exc_info=True,
                    extra={
                        'operation': operation_name,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
                raise
        
        return wrapper
    return decorator