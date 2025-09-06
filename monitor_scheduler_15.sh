#!/bin/bash
# Script para monitorear la ejecución del scheduler a las 15:00

echo '🕐 Monitoreando ejecución del scheduler programado para las 15:00...'
echo 'Hora actual: Sat Sep  6 10:45:50 -04 2025'
echo ''
echo 'Esperando logs del scheduler (Ctrl+C para salir)...'

# Monitorear logs en tiempo real filtrando por scheduler
heroku logs --tail --app informediariochile | grep -E 'scheduler|enviar_informes|Starting process with command'
