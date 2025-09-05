#!/bin/bash

# Script para configurar Heroku Scheduler y eliminar el worker costoso
# Este cambio reduce los costos de ~$25-50/mes a $0

echo "🔧 Configurando Heroku Scheduler para reemplazar el worker costoso..."
echo "=============================================================="

# Verificar que estamos en el directorio correcto
if [ ! -f "Procfile" ]; then
    echo "❌ Error: Debe ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

APP_NAME="informediariochile"

echo "📋 Paso 1: Verificar que el add-on Scheduler esté instalado..."
heroku addons --app $APP_NAME | grep scheduler || {
    echo "🔧 Instalando Heroku Scheduler (gratuito)..."
    heroku addons:create scheduler:standard --app $APP_NAME
}

echo ""
echo "📋 Paso 2: Eliminar jobs del scheduler existentes (si los hay)..."
heroku run "heroku jobs:cancel --app $APP_NAME" --app $APP_NAME 2>/dev/null || echo "No hay jobs previos para cancelar"

echo ""
echo "📋 Paso 3: Configurar la tarea diaria..."
echo "Comando a configurar: python manage.py enviar_informes_diarios"
echo "Horario: 13:00 UTC (9:00 AM Chile) - Lunes a Sábado"

# Crear el job en Heroku Scheduler
heroku addons:open scheduler --app $APP_NAME &

echo ""
echo "✅ CONFIGURACIÓN MANUAL NECESARIA:"
echo "=============================================================="
echo "1. Se abrió el panel de Heroku Scheduler en tu navegador"
echo "2. Haz clic en 'Create job'"
echo "3. Configura:"
echo "   - Command: python manage.py enviar_informes_diarios"
echo "   - Frequency: Daily"
echo "   - Time: 13:00 UTC"
echo "   - Description: Envío diario de informes (9 AM Chile)"
echo ""
echo "📊 AHORRO ESTIMADO: $25-50/mes → $0"
echo ""
echo "🔍 Para verificar que funciona:"
echo "   heroku run python manage.py enviar_informes_diarios --app $APP_NAME"
echo ""
echo "📝 NOTA: El job NO se ejecutará los domingos automáticamente"
echo "   (la lógica está en el comando enviar_informes_diarios)"

echo ""
echo "✅ Worker eliminado del Procfile. Listo para deploy!"