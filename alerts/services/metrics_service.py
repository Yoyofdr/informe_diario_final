"""
Servicio para registrar y gestionar métricas del sistema
"""
import time
import psutil
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from alerts.models import ScrapingMetric, PDFProcessingMetric, APICallMetric

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Recolector de métricas para el proceso de scraping"""
    
    def __init__(self):
        self.current_metric: Optional[ScrapingMetric] = None
        self.start_time: Optional[float] = None
        self.pdf_counters = {
            'total': 0,
            'desde_cache': 0,
            'descargados': 0
        }
        self.pdf_times = []
        
    def start_scraping(self, fecha: datetime) -> ScrapingMetric:
        """Inicia el registro de métricas para una sesión de scraping"""
        self.start_time = time.time()
        self.current_metric = ScrapingMetric.objects.create(
            fecha_scraping=fecha,
            exitoso=False  # Se marcará como exitoso al final si todo va bien
        )
        
        # Registrar uso de memoria inicial
        try:
            process = psutil.Process()
            self.current_metric.memoria_usada_mb = process.memory_info().rss / 1024 / 1024
            self.current_metric.save()
        except:
            pass
            
        return self.current_metric
    
    def end_scraping(self, exitoso: bool = True, mensaje_error: str = None):
        """Finaliza el registro de métricas"""
        if not self.current_metric:
            return
            
        end_time = time.time()
        self.current_metric.duracion_segundos = end_time - self.start_time
        self.current_metric.exitoso = exitoso
        self.current_metric.mensaje_error = mensaje_error
        
        # Actualizar contadores
        self.current_metric.pdfs_descargados = self.pdf_counters['descargados']
        self.current_metric.pdfs_desde_cache = self.pdf_counters['desde_cache']
        
        # Calcular promedios
        if self.pdf_times:
            self.current_metric.tiempo_descarga_promedio = sum(self.pdf_times) / len(self.pdf_times)
            
        self.current_metric.save()
        
    def add_publicacion(self, es_relevante: bool = False):
        """Registra una publicación procesada"""
        if self.current_metric:
            self.current_metric.total_publicaciones += 1
            if es_relevante:
                self.current_metric.publicaciones_relevantes += 1
            self.current_metric.save()
    
    @contextmanager
    def track_pdf_processing(self, url: str, titulo: str):
        """Context manager para trackear el procesamiento de un PDF"""
        start_time = time.time()
        pdf_metric = None
        
        if self.current_metric:
            pdf_metric = PDFProcessingMetric.objects.create(
                scraping_metric=self.current_metric,
                url_pdf=url,
                titulo=titulo[:500]  # Limitar longitud del título
            )
        
        try:
            yield pdf_metric
            if pdf_metric:
                pdf_metric.exitoso = True
        except Exception as e:
            if pdf_metric:
                pdf_metric.exitoso = False
                pdf_metric.mensaje_error = str(e)
            raise
        finally:
            if pdf_metric:
                total_time = time.time() - start_time
                pdf_metric.save()
                self.pdf_times.append(total_time)
    
    def record_pdf_download(self, tiempo_descarga: float, desde_cache: bool = False):
        """Registra una descarga de PDF"""
        if desde_cache:
            self.pdf_counters['desde_cache'] += 1
        else:
            self.pdf_counters['descargados'] += 1
            
    def record_pdf_extraction(self, pdf_metric: PDFProcessingMetric, metodo: str, tiempo: float):
        """Registra el método y tiempo de extracción de un PDF"""
        if pdf_metric:
            pdf_metric.metodo_extraccion = metodo
            pdf_metric.tiempo_extraccion = tiempo
            pdf_metric.save()
    
    def record_pdf_analysis(self, pdf_metric: PDFProcessingMetric, tiempo: float):
        """Registra el tiempo de análisis (resumen) de un PDF"""
        if pdf_metric:
            pdf_metric.tiempo_analisis = tiempo
            pdf_metric.save()
    
    def record_pdf_info(self, pdf_metric: PDFProcessingMetric, num_paginas: int = None, tamano_bytes: int = None):
        """Registra información adicional del PDF"""
        if pdf_metric:
            if num_paginas:
                pdf_metric.num_paginas = num_paginas
            if tamano_bytes:
                pdf_metric.tamano_bytes = tamano_bytes
            pdf_metric.save()


class APIMetricsCollector:
    """Recolector de métricas para llamadas a APIs"""
    
    @staticmethod
    @contextmanager
    def track_api_call(api_name: str, endpoint: str = None):
        """Context manager para trackear llamadas a APIs"""
        start_time = time.time()
        api_metric = APICallMetric.objects.create(
            api_name=api_name,
            endpoint=endpoint or '',
            exitoso=False
        )
        
        try:
            yield api_metric
            api_metric.exitoso = True
        except Exception as e:
            api_metric.mensaje_error = str(e)
            raise
        finally:
            api_metric.duracion_segundos = time.time() - start_time
            api_metric.save()
    
    @staticmethod
    def record_api_usage(api_metric: APICallMetric, tokens: int = None, costo: float = None):
        """Registra uso adicional de la API"""
        if api_metric:
            if tokens:
                api_metric.tokens_usados = tokens
            if costo:
                api_metric.costo_estimado = costo
            api_metric.save()


# Instancias globales para uso fácil
metrics_collector = MetricsCollector()
api_metrics = APIMetricsCollector()