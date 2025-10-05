#!/bin/bash
# Script mejorado para ejecutar el informe diario desde cron
# Este script actualiza el código antes de ejecutar

# Configurar el entorno
export PATH="/Users/rodrigofernandezdelrio/.pyenv/shims:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYENV_ROOT="/Users/rodrigofernandezdelrio/.pyenv"

# Cambiar al directorio del proyecto
cd "/Users/rodrigofernandezdelrio/Desktop/Project Diario Oficial"

echo "========================================"
echo "Ejecutando informe diario: $(date)"
echo "========================================"

# IMPORTANTE: Actualizar el código desde GitHub antes de ejecutar
echo "Actualizando código desde GitHub..."
git pull origin main

# Verificar si el pull fue exitoso
if [ $? -eq 0 ]; then
    echo "✓ Código actualizado exitosamente"
else
    echo "⚠ Advertencia: No se pudo actualizar el código, continuando con versión local"
fi

echo "----------------------------------------"

# Ejecutar el generador de informe oficial integrado mejorado
echo "Generando informe..."
/Users/rodrigofernandezdelrio/.pyenv/shims/python scripts/generators/generar_informe_oficial_integrado_mejorado.py

echo "Informe completado: $(date)"
echo "========================================"