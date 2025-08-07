"""
Sistema de caché para informes diarios usando la base de datos
Guarda el informe generado en la mañana para reutilizarlo durante el día
"""
from datetime import datetime
import pytz
from alerts.models import InformeDiarioCache


class CacheInformeDiario:
    """
    Maneja el caché del informe diario usando la base de datos
    """
    
    def _get_fecha_chile(self):
        """Obtiene la fecha actual en Chile"""
        chile_tz = pytz.timezone('America/Santiago')
        return datetime.now(chile_tz).date()
    
    def guardar_informe(self, html_content, fecha=None):
        """
        Guarda el informe HTML en la base de datos
        
        Args:
            html_content: Contenido HTML del informe
            fecha: Fecha del informe (date object). Si es None, usa fecha actual
        
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            if not fecha:
                fecha = self._get_fecha_chile()
            
            informe = InformeDiarioCache.save_report(
                fecha=fecha,
                html_content=html_content,
                metadata={
                    'generated_at': datetime.now().isoformat(),
                    'timezone': 'America/Santiago'
                }
            )
            
            print(f"✅ Informe guardado en base de datos para fecha: {fecha}")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando informe en base de datos: {str(e)}")
            return False
    
    def obtener_informe(self, fecha=None):
        """
        Obtiene el informe HTML de la base de datos
        
        Args:
            fecha: Fecha del informe (date object). Si es None, usa fecha actual
            
        Returns:
            str: HTML del informe o None si no existe
        """
        try:
            if not fecha:
                fecha = self._get_fecha_chile()
            
            informe = InformeDiarioCache.get_or_none(fecha)
            
            if not informe:
                print(f"⚠️ No hay informe en caché para {fecha}")
                return None
            
            print(f"✅ Informe recuperado de la base de datos: {fecha}")
            return informe.html_content
            
        except Exception as e:
            print(f"❌ Error leyendo informe de la base de datos: {str(e)}")
            return None
    
    def existe_informe_hoy(self):
        """
        Verifica si existe un informe en caché para hoy
        
        Returns:
            bool: True si existe informe de hoy
        """
        fecha_hoy = self._get_fecha_chile()
        informe = InformeDiarioCache.get_or_none(fecha_hoy)
        return informe is not None
    
    def limpiar_cache_antiguo(self, dias_mantener=7):
        """
        Limpia informes antiguos de la base de datos
        
        Args:
            dias_mantener: Número de días a mantener en caché
        """
        try:
            from datetime import timedelta
            fecha_limite = self._get_fecha_chile() - timedelta(days=dias_mantener)
            
            # Eliminar informes más antiguos que la fecha límite
            eliminados = InformeDiarioCache.objects.filter(fecha__lt=fecha_limite).delete()
            
            if eliminados[0] > 0:
                print(f"🗑️ Eliminados {eliminados[0]} informes antiguos de la base de datos")
        
        except Exception as e:
            print(f"❌ Error limpiando caché: {str(e)}")