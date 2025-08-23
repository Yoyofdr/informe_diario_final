"""
Sistema de caché para PDFs de CMF
Almacena PDFs descargados para evitar descargas repetidas y mejorar confiabilidad
"""
import os
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PDFCache:
    def __init__(self, cache_dir=None, max_age_hours=24):
        """
        Inicializa el sistema de caché de PDFs
        
        Args:
            cache_dir: Directorio donde almacenar los PDFs cacheados
            max_age_hours: Tiempo máximo en horas antes de considerar un caché obsoleto
        """
        if cache_dir is None:
            # Usar directorio temporal del sistema
            import tempfile
            cache_dir = Path(tempfile.gettempdir()) / "cmf_pdf_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(hours=max_age_hours)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()
        
    def _load_metadata(self):
        """Carga metadata del caché desde archivo"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error cargando metadata de caché: {e}")
        return {}
    
    def _save_metadata(self):
        """Guarda metadata del caché a archivo"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error guardando metadata de caché: {e}")
    
    def _get_cache_key(self, url):
        """Genera una clave única para la URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key):
        """Obtiene la ruta del archivo cacheado"""
        return self.cache_dir / f"{cache_key}.pdf"
    
    def _is_cache_valid(self, cache_key):
        """Verifica si el caché es válido (no ha expirado)"""
        if cache_key not in self.metadata:
            return False
        
        cached_time = datetime.fromisoformat(self.metadata[cache_key]['timestamp'])
        age = datetime.now() - cached_time
        
        return age < self.max_age
    
    def get(self, url):
        """
        Obtiene un PDF del caché si existe y es válido
        
        Args:
            url: URL del PDF
            
        Returns:
            bytes del PDF o None si no está en caché
        """
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists() and self._is_cache_valid(cache_key):
            try:
                with open(cache_path, 'rb') as f:
                    logger.info(f"✅ PDF obtenido del caché: {url[:50]}...")
                    return f.read()
            except Exception as e:
                logger.error(f"Error leyendo PDF del caché: {e}")
        
        return None
    
    def put(self, url, pdf_content):
        """
        Almacena un PDF en el caché
        
        Args:
            url: URL del PDF
            pdf_content: Contenido del PDF en bytes
        """
        if not pdf_content:
            return
        
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            # Guardar PDF
            with open(cache_path, 'wb') as f:
                f.write(pdf_content)
            
            # Actualizar metadata
            self.metadata[cache_key] = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'size': len(pdf_content)
            }
            self._save_metadata()
            
            logger.info(f"📦 PDF guardado en caché: {url[:50]}...")
        except Exception as e:
            logger.error(f"Error guardando PDF en caché: {e}")
    
    def clear_old(self):
        """Limpia entradas de caché obsoletas"""
        current_time = datetime.now()
        keys_to_remove = []
        
        for cache_key, info in self.metadata.items():
            cached_time = datetime.fromisoformat(info['timestamp'])
            if current_time - cached_time > self.max_age:
                keys_to_remove.append(cache_key)
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                        logger.info(f"🗑️ Caché obsoleto eliminado: {cache_key}")
                    except Exception as e:
                        logger.error(f"Error eliminando caché: {e}")
        
        # Actualizar metadata
        for key in keys_to_remove:
            del self.metadata[key]
        
        if keys_to_remove:
            self._save_metadata()
            logger.info(f"Limpieza de caché completada: {len(keys_to_remove)} archivos eliminados")
    
    def get_stats(self):
        """Obtiene estadísticas del caché"""
        total_size = 0
        valid_count = 0
        expired_count = 0
        
        for cache_key, info in self.metadata.items():
            total_size += info.get('size', 0)
            if self._is_cache_valid(cache_key):
                valid_count += 1
            else:
                expired_count += 1
        
        return {
            'total_files': len(self.metadata),
            'valid_files': valid_count,
            'expired_files': expired_count,
            'total_size_mb': total_size / (1024 * 1024)
        }

# Instancia global del caché
pdf_cache = PDFCache()