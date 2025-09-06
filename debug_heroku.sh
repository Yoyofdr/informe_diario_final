#!/bin/bash

echo "🔍 DEBUG COMPLETO DE HEROKU SCHEDULER"
echo "======================================"
echo ""

echo "1. Verificando add-ons instalados:"
heroku addons --app informediariochile

echo ""
echo "2. Verificando variables críticas:"
heroku config:get EMAIL_HOST_USER --app informediariochile && echo "✅ EMAIL_HOST_USER configurado" || echo "❌ EMAIL_HOST_USER faltante"
heroku config:get OPENAI_API_KEY --app informediariochile && echo "✅ OPENAI_API_KEY configurado" || echo "❌ OPENAI_API_KEY faltante"
heroku config:get DATABASE_URL --app informediariochile && echo "✅ DATABASE_URL configurado" || echo "❌ DATABASE_URL faltante"

echo ""
echo "3. Probando comando directamente:"
heroku run "python -c 'from datetime import datetime; print(f\"Hora en Heroku: {datetime.now()}\"); import os; print(f\"Variables: {len(os.environ)}\")'" --app informediariochile

echo ""
echo "4. Buscando errores del scheduler en logs (últimas 24h):"
heroku logs --app informediariochile -n 1000 | grep -i "scheduler" | tail -10

echo ""
echo "5. Verificando si hay crashes o errores R14 (memoria):"
heroku logs --app informediariochile -n 1000 | grep -E "Error R|crashed" | tail -5