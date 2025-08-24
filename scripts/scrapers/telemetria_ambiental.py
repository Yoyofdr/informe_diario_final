"""
Sistema de telemetría y monitoreo para scrapers ambientales
Rastrea métricas, errores y healthchecks
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)

class TelemetriaAmbiental:
    """
    Sistema de telemetría para monitorear scrapers ambientales
    """
    
    def __init__(self, metrics_dir: str = None):
        self.metrics_dir = Path(metrics_dir or "/tmp/telemetria_ambiental")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.metrics_dir / "metrics.json"
        self.errors_file = self.metrics_dir / "errors.json"
        self.health_file = self.metrics_dir / "health.json"
        
        # Cargar métricas existentes
        self.metrics = self._cargar_metricas()
        self.errors = self._cargar_errores()
        
    def registrar_extraccion(self, fuente: str, resultado: Dict):
        """
        Registra una extracción exitosa o fallida
        
        Args:
            fuente: 'SEA', 'SMA', 'SNIFA', etc.
            resultado: Dict con datos de la extracción
        """
        timestamp = datetime.now().isoformat()
        
        metrica = {
            'timestamp': timestamp,
            'fuente': fuente,
            'items_extraidos': resultado.get('total_items', 0),
            'tiempo_ms': resultado.get('tiempo_ms', 0),
            'exitoso': resultado.get('exitoso', False),
            'tipo_datos': resultado.get('tipo_datos', []),
            'errores': resultado.get('errores', [])
        }
        
        # Agregar a métricas históricas
        if fuente not in self.metrics:
            self.metrics[fuente] = []
        
        self.metrics[fuente].append(metrica)
        
        # Mantener solo últimos 30 días
        self._limpiar_metricas_antiguas(fuente)
        
        # Guardar
        self._guardar_metricas()
        
        # Si hubo errores, registrarlos también
        if not resultado.get('exitoso') or resultado.get('errores'):
            self.registrar_error(fuente, resultado.get('errores', ['Error desconocido']))
        
        # Actualizar health status
        self._actualizar_health_status(fuente, resultado)
        
        logger.info(f"📊 Telemetría registrada para {fuente}: {metrica['items_extraidos']} items")
    
    def registrar_error(self, fuente: str, errores: List[str]):
        """
        Registra errores específicos
        """
        timestamp = datetime.now().isoformat()
        
        error_entry = {
            'timestamp': timestamp,
            'fuente': fuente,
            'errores': errores if isinstance(errores, list) else [str(errores)]
        }
        
        if fuente not in self.errors:
            self.errors[fuente] = []
        
        self.errors[fuente].append(error_entry)
        
        # Mantener solo últimos 7 días de errores
        self._limpiar_errores_antiguos(fuente)
        
        self._guardar_errores()
        
        logger.error(f"❌ Error registrado para {fuente}: {errores}")
    
    def obtener_estadisticas(self, fuente: str = None, dias: int = 7) -> Dict:
        """
        Obtiene estadísticas de los últimos N días
        """
        fecha_limite = datetime.now() - timedelta(days=dias)
        stats = {}
        
        fuentes = [fuente] if fuente else self.metrics.keys()
        
        for f in fuentes:
            metricas_fuente = self.metrics.get(f, [])
            
            # Filtrar por fecha
            metricas_recientes = [
                m for m in metricas_fuente
                if datetime.fromisoformat(m['timestamp']) >= fecha_limite
            ]
            
            if metricas_recientes:
                items_por_dia = [m['items_extraidos'] for m in metricas_recientes]
                tiempos = [m['tiempo_ms'] for m in metricas_recientes if m['tiempo_ms'] > 0]
                exitosos = sum(1 for m in metricas_recientes if m['exitoso'])
                
                stats[f] = {
                    'total_extracciones': len(metricas_recientes),
                    'exitosas': exitosos,
                    'fallidas': len(metricas_recientes) - exitosos,
                    'tasa_exito': (exitosos / len(metricas_recientes)) * 100 if metricas_recientes else 0,
                    'items_promedio': statistics.mean(items_por_dia) if items_por_dia else 0,
                    'items_max': max(items_por_dia) if items_por_dia else 0,
                    'items_min': min(items_por_dia) if items_por_dia else 0,
                    'tiempo_promedio_ms': statistics.mean(tiempos) if tiempos else 0,
                    'ultimo_exito': self._obtener_ultimo_exito(f),
                    'errores_recientes': len(self.errors.get(f, []))
                }
            else:
                stats[f] = {
                    'total_extracciones': 0,
                    'mensaje': 'Sin datos en el período'
                }
        
        return stats
    
    def verificar_health(self) -> Dict:
        """
        Verifica el estado de salud de todos los scrapers
        """
        health = {}
        
        for fuente in ['SEA', 'SMA', 'SNIFA']:
            health[fuente] = self._verificar_health_fuente(fuente)
        
        # Estado general
        health['general'] = {
            'estado': 'OK' if all(h['estado'] == 'OK' for h in health.values() if isinstance(h, dict)) else 'DEGRADED',
            'timestamp': datetime.now().isoformat(),
            'resumen': self._generar_resumen_health(health)
        }
        
        # Guardar health status
        self._guardar_health(health)
        
        return health
    
    def obtener_alertas(self) -> List[Dict]:
        """
        Genera alertas basadas en anomalías detectadas
        """
        alertas = []
        stats = self.obtener_estadisticas(dias=3)
        
        for fuente, stat in stats.items():
            if isinstance(stat, dict) and 'tasa_exito' in stat:
                # Alerta por baja tasa de éxito
                if stat['tasa_exito'] < 80:
                    alertas.append({
                        'tipo': 'TASA_EXITO_BAJA',
                        'fuente': fuente,
                        'mensaje': f"{fuente}: Tasa de éxito {stat['tasa_exito']:.1f}% (umbral: 80%)",
                        'severidad': 'alta' if stat['tasa_exito'] < 50 else 'media'
                    })
                
                # Alerta por caída en items extraídos
                if stat['items_promedio'] > 0:
                    stats_7d = self.obtener_estadisticas(fuente, dias=7)
                    stats_1d = self.obtener_estadisticas(fuente, dias=1)
                    
                    if fuente in stats_7d and fuente in stats_1d:
                        promedio_7d = stats_7d[fuente].get('items_promedio', 0)
                        promedio_1d = stats_1d[fuente].get('items_promedio', 0)
                        
                        if promedio_7d > 0 and promedio_1d < promedio_7d * 0.5:
                            alertas.append({
                                'tipo': 'CAIDA_ITEMS',
                                'fuente': fuente,
                                'mensaje': f"{fuente}: Items extraídos cayó 50% vs promedio semanal",
                                'severidad': 'media'
                            })
                
                # Alerta por tiempo de respuesta alto
                if stat.get('tiempo_promedio_ms', 0) > 30000:  # Más de 30 segundos
                    alertas.append({
                        'tipo': 'TIEMPO_ALTO',
                        'fuente': fuente,
                        'mensaje': f"{fuente}: Tiempo promedio {stat['tiempo_promedio_ms']/1000:.1f}s (umbral: 30s)",
                        'severidad': 'baja'
                    })
        
        return alertas
    
    def generar_reporte_diario(self) -> str:
        """
        Genera un reporte diario en formato markdown
        """
        ahora = datetime.now()
        reporte = []
        
        reporte.append(f"# 📊 Reporte de Telemetría Ambiental")
        reporte.append(f"**Fecha:** {ahora.strftime('%d/%m/%Y %H:%M')}\n")
        
        # Health Status
        health = self.verificar_health()
        reporte.append("## 🏥 Estado de Salud\n")
        
        for fuente, status in health.items():
            if fuente != 'general' and isinstance(status, dict):
                emoji = "✅" if status['estado'] == 'OK' else "⚠️" if status['estado'] == 'DEGRADED' else "❌"
                reporte.append(f"- **{fuente}**: {emoji} {status['estado']} - {status.get('mensaje', '')}")
        
        # Estadísticas
        reporte.append("\n## 📈 Estadísticas (Últimos 7 días)\n")
        stats = self.obtener_estadisticas(dias=7)
        
        for fuente, stat in stats.items():
            if 'tasa_exito' in stat:
                reporte.append(f"\n### {fuente}")
                reporte.append(f"- Extracciones: {stat['total_extracciones']} (✅ {stat['exitosas']} / ❌ {stat['fallidas']})")
                reporte.append(f"- Tasa de éxito: {stat['tasa_exito']:.1f}%")
                reporte.append(f"- Items promedio: {stat['items_promedio']:.1f}")
                reporte.append(f"- Tiempo promedio: {stat['tiempo_promedio_ms']/1000:.1f}s")
        
        # Alertas
        alertas = self.obtener_alertas()
        if alertas:
            reporte.append("\n## ⚠️ Alertas Activas\n")
            for alerta in alertas:
                emoji = "🔴" if alerta['severidad'] == 'alta' else "🟡" if alerta['severidad'] == 'media' else "🔵"
                reporte.append(f"- {emoji} {alerta['mensaje']}")
        
        # Errores recientes
        reporte.append("\n## 🐛 Errores Recientes (Últimas 24h)\n")
        errores_24h = self._obtener_errores_recientes(horas=24)
        
        if errores_24h:
            for fuente, errores in errores_24h.items():
                reporte.append(f"\n### {fuente}")
                for error in errores[:3]:  # Máximo 3 errores por fuente
                    reporte.append(f"- {error['timestamp']}: {', '.join(error['errores'][:2])}")
        else:
            reporte.append("✅ Sin errores en las últimas 24 horas")
        
        # Recomendaciones
        reporte.append("\n## 💡 Recomendaciones\n")
        recomendaciones = self._generar_recomendaciones(stats, alertas)
        for rec in recomendaciones:
            reporte.append(f"- {rec}")
        
        return "\n".join(reporte)
    
    # Métodos privados auxiliares
    
    def _cargar_metricas(self) -> Dict:
        """Carga métricas desde archivo"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _cargar_errores(self) -> Dict:
        """Carga errores desde archivo"""
        if self.errors_file.exists():
            try:
                with open(self.errors_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _guardar_metricas(self):
        """Guarda métricas en archivo"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
    
    def _guardar_errores(self):
        """Guarda errores en archivo"""
        with open(self.errors_file, 'w') as f:
            json.dump(self.errors, f, indent=2, ensure_ascii=False)
    
    def _guardar_health(self, health: Dict):
        """Guarda estado de salud"""
        with open(self.health_file, 'w') as f:
            json.dump(health, f, indent=2, ensure_ascii=False)
    
    def _limpiar_metricas_antiguas(self, fuente: str, dias: int = 30):
        """Limpia métricas más antiguas que N días"""
        if fuente in self.metrics:
            fecha_limite = datetime.now() - timedelta(days=dias)
            self.metrics[fuente] = [
                m for m in self.metrics[fuente]
                if datetime.fromisoformat(m['timestamp']) >= fecha_limite
            ]
    
    def _limpiar_errores_antiguos(self, fuente: str, dias: int = 7):
        """Limpia errores más antiguos que N días"""
        if fuente in self.errors:
            fecha_limite = datetime.now() - timedelta(days=dias)
            self.errors[fuente] = [
                e for e in self.errors[fuente]
                if datetime.fromisoformat(e['timestamp']) >= fecha_limite
            ]
    
    def _obtener_ultimo_exito(self, fuente: str) -> Optional[str]:
        """Obtiene timestamp del último éxito"""
        metricas = self.metrics.get(fuente, [])
        for m in reversed(metricas):
            if m.get('exitoso'):
                return m['timestamp']
        return None
    
    def _verificar_health_fuente(self, fuente: str) -> Dict:
        """Verifica health de una fuente específica"""
        stats_24h = self.obtener_estadisticas(fuente, dias=1)
        
        if fuente not in stats_24h or stats_24h[fuente].get('total_extracciones', 0) == 0:
            return {
                'estado': 'UNKNOWN',
                'mensaje': 'Sin datos en las últimas 24 horas'
            }
        
        stat = stats_24h[fuente]
        
        # Determinar estado
        if stat['tasa_exito'] >= 90:
            estado = 'OK'
            mensaje = f"Funcionando correctamente ({stat['tasa_exito']:.0f}% éxito)"
        elif stat['tasa_exito'] >= 70:
            estado = 'DEGRADED'
            mensaje = f"Funcionamiento degradado ({stat['tasa_exito']:.0f}% éxito)"
        else:
            estado = 'ERROR'
            mensaje = f"Múltiples fallos ({stat['tasa_exito']:.0f}% éxito)"
        
        return {
            'estado': estado,
            'mensaje': mensaje,
            'ultimo_exito': stat.get('ultimo_exito'),
            'items_promedio': stat.get('items_promedio', 0)
        }
    
    def _generar_resumen_health(self, health: Dict) -> str:
        """Genera resumen de health"""
        estados = [h['estado'] for h in health.values() if isinstance(h, dict) and 'estado' in h]
        
        ok = sum(1 for e in estados if e == 'OK')
        degraded = sum(1 for e in estados if e == 'DEGRADED')
        error = sum(1 for e in estados if e == 'ERROR')
        
        return f"OK: {ok}, Degradado: {degraded}, Error: {error}"
    
    def _obtener_errores_recientes(self, horas: int = 24) -> Dict:
        """Obtiene errores de las últimas N horas"""
        fecha_limite = datetime.now() - timedelta(hours=horas)
        errores_recientes = {}
        
        for fuente, errores in self.errors.items():
            errores_filtrados = [
                e for e in errores
                if datetime.fromisoformat(e['timestamp']) >= fecha_limite
            ]
            if errores_filtrados:
                errores_recientes[fuente] = errores_filtrados
        
        return errores_recientes
    
    def _generar_recomendaciones(self, stats: Dict, alertas: List[Dict]) -> List[str]:
        """Genera recomendaciones basadas en telemetría"""
        recomendaciones = []
        
        # Analizar alertas
        for alerta in alertas:
            if alerta['tipo'] == 'TASA_EXITO_BAJA':
                recomendaciones.append(f"Revisar logs de {alerta['fuente']} para identificar causa de fallos")
            elif alerta['tipo'] == 'TIEMPO_ALTO':
                recomendaciones.append(f"Optimizar queries o aumentar timeout para {alerta['fuente']}")
            elif alerta['tipo'] == 'CAIDA_ITEMS':
                recomendaciones.append(f"Verificar si hubo cambios en la estructura de {alerta['fuente']}")
        
        # Recomendaciones generales
        for fuente, stat in stats.items():
            if isinstance(stat, dict) and stat.get('items_promedio', 0) == 0:
                recomendaciones.append(f"Verificar acceso a API/sitio de {fuente}")
        
        if not recomendaciones:
            recomendaciones.append("Sistema funcionando normalmente, sin acciones requeridas")
        
        return recomendaciones
    
    def _actualizar_health_status(self, fuente: str, resultado: Dict):
        """Actualiza el estado de salud basado en resultado reciente"""
        # Este método es llamado automáticamente al registrar extracción
        pass


# Singleton global
telemetria = TelemetriaAmbiental()


def test_telemetria():
    """Prueba el sistema de telemetría"""
    print("\n" + "="*70)
    print("🔬 PRUEBA SISTEMA DE TELEMETRÍA")
    print("="*70)
    
    # Simular algunas extracciones
    telemetria.registrar_extraccion('SEA', {
        'total_items': 15,
        'tiempo_ms': 2500,
        'exitoso': True,
        'tipo_datos': ['proyectos', 'pac']
    })
    
    telemetria.registrar_extraccion('SMA', {
        'total_items': 8,
        'tiempo_ms': 1800,
        'exitoso': True,
        'tipo_datos': ['sanciones', 'procedimientos']
    })
    
    telemetria.registrar_extraccion('SNIFA', {
        'total_items': 0,
        'tiempo_ms': 5000,
        'exitoso': False,
        'errores': ['Timeout al conectar con API', 'Sin respuesta del servidor']
    })
    
    # Generar reporte
    print("\n" + telemetria.generar_reporte_diario())
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    test_telemetria()