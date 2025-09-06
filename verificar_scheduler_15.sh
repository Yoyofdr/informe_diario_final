#!/bin/bash

echo "📧 VERIFICACIÓN DE SCHEDULER A LAS 15:00"
echo "========================================="
echo ""

# Mostrar hora actual
echo "⏰ Hora actual: $(date '+%H:%M:%S - %d/%m/%Y')"
echo ""

# Verificar últimas ejecuciones del scheduler
echo "🔍 Buscando ejecuciones recientes del scheduler..."
heroku logs --app informediariochile -n 100 | grep -E "scheduler\.|enviar_informes" | tail -5

echo ""
echo "📊 Para monitorear en tiempo real:"
echo "heroku logs --tail --app informediariochile | grep scheduler"
echo ""
echo "✅ El scheduler debería ejecutarse a las 15:00 (3:00 PM)"
echo "📧 Revisa tu correo después de las 15:00"