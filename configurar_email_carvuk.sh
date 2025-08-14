#!/bin/bash

echo "🔧 Configurando email rodrigo@carvuk.com para mejor entregabilidad en Outlook..."
echo ""
echo "⚠️  IMPORTANTE: Necesitarás la contraseña de aplicación de Gmail para rodrigo@carvuk.com"
echo ""
echo "Para obtener la contraseña de aplicación:"
echo "1. Ve a https://myaccount.google.com/security"
echo "2. Busca 'Contraseñas de aplicaciones' (App passwords)"
echo "3. Genera una nueva contraseña para 'Mail'"
echo "4. Copia la contraseña de 16 caracteres"
echo ""
read -p "Ingresa la contraseña de aplicación de Gmail: " gmail_password

# Configurar las variables en Heroku
echo ""
echo "📤 Configurando variables en Heroku..."

heroku config:set CARVUK_EMAIL_PASSWORD="$gmail_password" --app informediariochile
heroku config:set SMTP_SERVER_CARVUK="smtp.gmail.com" --app informediariochile
heroku config:set SMTP_PORT_CARVUK="587" --app informediariochile

echo ""
echo "✅ Configuración completada"
echo ""
echo "📧 El sistema ahora enviará emails desde: rodrigo@carvuk.com"
echo "🎯 Esto debería mejorar significativamente la entrega en Outlook/Microsoft 365"
echo ""
echo "Próximos pasos:"
echo "1. Hacer git add, commit y push para desplegar los cambios"
echo "2. Los emails de mañana (9 AM) se enviarán con la nueva configuración"