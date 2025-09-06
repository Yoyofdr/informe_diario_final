#!/bin/bash

echo "🔍 Buscando logs del Scheduler de los últimos 2 días..."
echo "=================================================="

# Buscar logs del scheduler
heroku logs --app informediariochile -n 2000 | grep -E "scheduler\.|Starting process with command|enviar_informes|Error R|crashed|timeout|memory" > scheduler_debug.log

echo "📊 Resumen de lo encontrado:"
echo ""

echo "1. Intentos del Scheduler:"
grep -c "scheduler\." scheduler_debug.log || echo "0 intentos encontrados"

echo ""
echo "2. Ejecuciones del comando:"
grep -c "enviar_informes" scheduler_debug.log || echo "0 ejecuciones encontradas"

echo ""
echo "3. Errores de memoria/timeout:"
grep -E "Error R|memory|timeout" scheduler_debug.log | head -5

echo ""
echo "4. Últimas 10 líneas relacionadas con scheduler:"
grep -E "scheduler|enviar_informes" scheduler_debug.log | tail -10

echo ""
echo "📝 Log completo guardado en: scheduler_debug.log"