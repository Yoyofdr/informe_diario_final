#!/bin/bash
# Script para ejecutar el informe diario desde cron

# Configurar el entorno
export PATH="/Users/rodrigofernandezdelrio/.pyenv/shims:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYENV_ROOT="/Users/rodrigofernandezdelrio/.pyenv"

# Cambiar al directorio del proyecto
cd "/Users/rodrigofernandezdelrio/Desktop/Project Diario Oficial"

# Ejecutar el generador de informe oficial integrado mejorado
echo "========================================"
echo "Ejecutando informe diario: $(date)"
echo "========================================"

# Usar Python del sistema directamente con pyenv
/Users/rodrigofernandezdelrio/.pyenv/shims/python scripts/generators/generar_informe_oficial_integrado_mejorado.py

echo "Informe completado: $(date)"
echo "========================================"