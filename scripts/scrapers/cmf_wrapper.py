#!/usr/bin/env python3
"""
Wrapper para el scraper CMF para compatibilidad
"""

import subprocess
import json
import sys
from pathlib import Path

def obtener_hechos_esenciales_dia(fecha_str=None):
    """
    Wrapper para obtener hechos esenciales del día
    fecha_str: formato dd-mm-yyyy o None para hoy
    """
    script_path = Path(__file__).parent / "scraper_cmf_mejorado.py"
    
    if fecha_str:
        cmd = [sys.executable, str(script_path), fecha_str]
    else:
        cmd = [sys.executable, str(script_path)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Buscar JSON en el output
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('['):
                try:
                    return json.loads(line)
                except:
                    pass
        
        return []
    except Exception as e:
        print(f"Error ejecutando scraper CMF: {e}")
        return []