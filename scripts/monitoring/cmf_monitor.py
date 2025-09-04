#!/usr/bin/env python3
"""
Sistema de monitoreo para detectar problemas en el procesamiento de CMF
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

class CMFMonitor:
    """Monitor de salud del sistema de procesamiento CMF"""
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path("logs/monitoring")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.stats_file = self.log_dir / "cmf_stats.json"
        self.alerts_file = self.log_dir / "cmf_alerts.json"
        
    def log_processing(self, fecha: str, stats: Dict):
        """
        Registra estadísticas de procesamiento
        
        Args:
            fecha: Fecha del procesamiento
            stats: Dict con estadísticas (total, exitosos, fallidos, etc.)
        """
        # Cargar estadísticas históricas
        history = self._load_stats()
        
        # Agregar nueva entrada
        entry = {
            "fecha": fecha,
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }
        history.append(entry)
        
        # Mantener solo últimos 30 días
        if len(history) > 30:
            history = history[-30:]
        
        # Guardar
        self._save_stats(history)
        
        # Verificar alertas
        self._check_alerts(stats, history)
    
    def _check_alerts(self, current_stats: Dict, history: List):
        """
        Verifica condiciones de alerta y las registra
        """
        alerts = []
        
        # Alerta 1: Tasa de éxito < 80%
        if current_stats.get("total", 0) > 0:
            success_rate = current_stats.get("exitosos", 0) / current_stats["total"]
            if success_rate < 0.8:
                alerts.append({
                    "tipo": "TASA_EXITO_BAJA",
                    "mensaje": f"Tasa de éxito: {success_rate*100:.1f}%",
                    "severidad": "alta",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Alerta 2: Más de 5 timeouts
        if current_stats.get("timeout", 0) > 5:
            alerts.append({
                "tipo": "TIMEOUTS_EXCESIVOS",
                "mensaje": f"Timeouts: {current_stats['timeout']}",
                "severidad": "media",
                "timestamp": datetime.now().isoformat()
            })
        
        # Alerta 3: Texto corrupto en más del 20% de casos
        if current_stats.get("total", 0) > 0:
            corrupt_rate = current_stats.get("texto_corrupto", 0) / current_stats["total"]
            if corrupt_rate > 0.2:
                alerts.append({
                    "tipo": "TEXTO_CORRUPTO_ALTO",
                    "mensaje": f"Texto corrupto: {corrupt_rate*100:.1f}%",
                    "severidad": "alta",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Alerta 4: Degradación vs promedio histórico
        if len(history) >= 7:
            # Calcular promedio de últimos 7 días
            recent_rates = []
            for entry in history[-7:]:
                if entry["stats"].get("total", 0) > 0:
                    rate = entry["stats"].get("exitosos", 0) / entry["stats"]["total"]
                    recent_rates.append(rate)
            
            if recent_rates:
                avg_rate = sum(recent_rates) / len(recent_rates)
                current_rate = success_rate if current_stats.get("total", 0) > 0 else 0
                
                if current_rate < avg_rate * 0.8:  # 20% peor que promedio
                    alerts.append({
                        "tipo": "DEGRADACION_RENDIMIENTO",
                        "mensaje": f"Rendimiento degradado: {current_rate*100:.1f}% vs promedio {avg_rate*100:.1f}%",
                        "severidad": "alta",
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Guardar alertas si hay
        if alerts:
            self._save_alerts(alerts)
            self._notify_alerts(alerts)
    
    def _notify_alerts(self, alerts: List[Dict]):
        """
        Notifica alertas críticas
        """
        for alert in alerts:
            if alert["severidad"] == "alta":
                logger.error(f"🚨 ALERTA CMF: {alert['tipo']} - {alert['mensaje']}")
            else:
                logger.warning(f"⚠️ Advertencia CMF: {alert['tipo']} - {alert['mensaje']}")
    
    def get_health_status(self) -> Dict:
        """
        Obtiene el estado de salud actual del sistema
        """
        history = self._load_stats()
        
        if not history:
            return {"status": "sin_datos", "mensaje": "No hay datos históricos"}
        
        # Analizar últimos 7 días
        recent = history[-7:] if len(history) >= 7 else history
        
        total_procesados = sum(e["stats"].get("total", 0) for e in recent)
        total_exitosos = sum(e["stats"].get("exitosos", 0) for e in recent)
        total_fallidos = sum(e["stats"].get("fallidos", 0) for e in recent)
        total_timeouts = sum(e["stats"].get("timeout", 0) for e in recent)
        total_corrupto = sum(e["stats"].get("texto_corrupto", 0) for e in recent)
        
        if total_procesados > 0:
            success_rate = total_exitosos / total_procesados
            
            # Determinar estado
            if success_rate >= 0.95:
                status = "excelente"
            elif success_rate >= 0.85:
                status = "bueno"
            elif success_rate >= 0.70:
                status = "regular"
            else:
                status = "crítico"
            
            return {
                "status": status,
                "success_rate": success_rate,
                "stats": {
                    "total": total_procesados,
                    "exitosos": total_exitosos,
                    "fallidos": total_fallidos,
                    "timeouts": total_timeouts,
                    "texto_corrupto": total_corrupto
                },
                "periodo": f"Últimos {len(recent)} días"
            }
        
        return {"status": "sin_datos", "mensaje": "No hay procesamiento reciente"}
    
    def _load_stats(self) -> List:
        """Carga estadísticas históricas"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_stats(self, stats: List):
        """Guarda estadísticas"""
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def _save_alerts(self, alerts: List):
        """Guarda alertas"""
        # Cargar alertas existentes
        existing = []
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                existing = json.load(f)
        
        # Agregar nuevas
        existing.extend(alerts)
        
        # Mantener solo últimas 100
        if len(existing) > 100:
            existing = existing[-100:]
        
        # Guardar
        with open(self.alerts_file, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def generate_report(self) -> str:
        """
        Genera un reporte de salud del sistema
        """
        health = self.get_health_status()
        
        report = []
        report.append("=" * 60)
        report.append("📊 REPORTE DE SALUD - SISTEMA CMF")
        report.append("=" * 60)
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("")
        
        if health["status"] != "sin_datos":
            status_emoji = {
                "excelente": "✅",
                "bueno": "👍",
                "regular": "⚠️",
                "crítico": "🚨"
            }.get(health["status"], "❓")
            
            report.append(f"Estado: {status_emoji} {health['status'].upper()}")
            report.append(f"Tasa de éxito: {health['success_rate']*100:.1f}%")
            report.append(f"Período: {health['periodo']}")
            report.append("")
            report.append("Estadísticas:")
            for key, value in health["stats"].items():
                report.append(f"  - {key}: {value}")
        else:
            report.append(f"Estado: {health['mensaje']}")
        
        # Agregar alertas recientes
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                alerts = json.load(f)
                recent_alerts = alerts[-5:] if len(alerts) > 5 else alerts
                
                if recent_alerts:
                    report.append("")
                    report.append("Alertas recientes:")
                    for alert in recent_alerts:
                        report.append(f"  - [{alert['severidad']}] {alert['tipo']}: {alert['mensaje']}")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# Función helper para integrar con el generador de informes
def log_cmf_stats(fecha: str, total: int, exitosos: int, fallidos: int = 0, 
                  timeout: int = 0, texto_corrupto: int = 0):
    """
    Función conveniente para registrar estadísticas desde el generador
    """
    monitor = CMFMonitor()
    stats = {
        "total": total,
        "exitosos": exitosos,
        "fallidos": fallidos,
        "timeout": timeout,
        "texto_corrupto": texto_corrupto
    }
    monitor.log_processing(fecha, stats)
    
    # Retornar estado de salud
    return monitor.get_health_status()