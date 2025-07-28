"""
Utilidades para optimización de consultas a la base de datos
"""
from django.db.models import Prefetch, QuerySet
from typing import List, Optional


def optimize_empresa_queries(queryset: QuerySet) -> QuerySet:
    """
    Optimiza las consultas de Empresa para incluir relaciones comunes.
    """
    return queryset.select_related(
        # No hay ForeignKeys directos en Empresa
    ).prefetch_related(
        'hechosesenciales',  # Prefetch los hechos esenciales relacionados
        'informes_enviados',  # Prefetch los informes enviados
    )


def optimize_hecho_esencial_queries(queryset: QuerySet) -> QuerySet:
    """
    Optimiza las consultas de HechoEsencial.
    """
    return queryset.select_related(
        'empresa'  # Incluir datos de la empresa
    ).prefetch_related(
        'notificacionenviada_set'  # Prefetch notificaciones enviadas
    )


def optimize_destinatario_queries(queryset: QuerySet) -> QuerySet:
    """
    Optimiza las consultas de Destinatario.
    """
    return queryset.select_related(
        'organizacion',  # Incluir datos de la organización
        'organizacion__admin'  # Incluir el admin de la organización
    )


def optimize_informe_enviado_queries(queryset: QuerySet) -> QuerySet:
    """
    Optimiza las consultas de InformeEnviado.
    """
    return queryset.select_related(
        'empresa'  # Incluir datos de la empresa
    )


def optimize_organizacion_queries(queryset: QuerySet) -> QuerySet:
    """
    Optimiza las consultas de Organizacion.
    """
    return queryset.select_related(
        'admin'  # Incluir datos del usuario admin
    ).prefetch_related(
        'destinatarios',  # Prefetch destinatarios
        'pagos'  # Prefetch registros de pago
    )


def optimize_metrics_queries(queryset: QuerySet) -> QuerySet:
    """
    Optimiza las consultas de métricas de scraping.
    """
    from alerts.models import PDFProcessingMetric
    
    return queryset.prefetch_related(
        Prefetch(
            'pdf_metrics',
            queryset=PDFProcessingMetric.objects.order_by('-tiempo_total')
        )
    )


class QueryOptimizer:
    """
    Clase helper para aplicar optimizaciones a queries de forma consistente.
    """
    
    @staticmethod
    def get_empresas_with_stats():
        """
        Obtiene empresas con estadísticas pre-calculadas.
        """
        from django.db.models import Count, Max, Q
        from alerts.models import Empresa
        
        return Empresa.objects.annotate(
            total_hechos=Count('hechosesenciales'),
            hechos_relevantes=Count(
                'hechosesenciales',
                filter=Q(hechosesenciales__relevancia__gte=2)
            ),
            ultimo_hecho_fecha=Max('hechosesenciales__fecha_publicacion'),
            total_informes=Count('informes_enviados')
        ).order_by('nombre')
    
    @staticmethod
    def get_organizaciones_with_stats():
        """
        Obtiene organizaciones con estadísticas.
        """
        from django.db.models import Count, Q
        from alerts.models import Organizacion
        
        return Organizacion.objects.select_related(
            'admin'
        ).annotate(
            total_destinatarios=Count('destinatarios'),
            destinatarios_activos=Count(
                'destinatarios',
                filter=Q(destinatarios__activo=True)
            )
        ).order_by('nombre')
    
    @staticmethod
    def get_recent_informes(days: int = 30, empresa_id: Optional[int] = None):
        """
        Obtiene informes recientes optimizados.
        """
        from django.utils import timezone
        from datetime import timedelta
        from alerts.models import InformeEnviado
        
        fecha_limite = timezone.now() - timedelta(days=days)
        
        queryset = InformeEnviado.objects.filter(
            fecha_envio__gte=fecha_limite
        ).select_related('empresa')
        
        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)
        
        return queryset.order_by('-fecha_envio')


# Decorador para optimizar vistas
def optimize_view_queries(model_name: str):
    """
    Decorador para aplicar optimizaciones automáticas a vistas.
    
    Uso:
        @optimize_view_queries('empresa')
        def mi_vista(request):
            empresas = Empresa.objects.all()
    """
    def decorator(view_func):
        from functools import wraps
        
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Aquí podrías agregar lógica para aplicar optimizaciones
            # basadas en el modelo, pero por ahora solo pasamos la vista
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator