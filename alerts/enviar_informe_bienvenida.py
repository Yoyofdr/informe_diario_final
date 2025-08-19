"""
Función para enviar correo de bienvenida a nuevos usuarios
"""
import os
import sys
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
import pytz
from dotenv import load_dotenv
from alerts.utils.cache_informe import CacheInformeDiario


# Cargar variables de entorno
env_path = os.path.join(settings.BASE_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)


def enviar_informe_bienvenida(email_destinatario, nombre_destinatario):
    """
    Envía el informe del día actual a un nuevo usuario.
    Si existe el informe del día en caché, lo envía.
    Si no existe, envía un correo de bienvenida simple.
    
    Args:
        email_destinatario (str): Email del nuevo usuario
        nombre_destinatario (str): Nombre completo del nuevo usuario
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    
    print(f"=== ENVIANDO INFORME DE BIENVENIDA A {email_destinatario} ===\n")
    
    try:
        # Intentar obtener el informe del día del caché
        cache = CacheInformeDiario()
        html_content = cache.obtener_informe()
        
        if html_content:
            # Si hay informe del día, enviarlo
            print(f"✅ Informe del día encontrado en caché, enviando...")
            subject = f"Informe Diario • {datetime.now(pytz.timezone('America/Santiago')).strftime('%d-%m-%Y')}"
        else:
            # Si no hay informe, enviar correo de bienvenida simple
            print(f"⚠️ No hay informe del día en caché, enviando correo de bienvenida...")
            subject = "Bienvenido a Informe Diario"
            # Crear mensaje HTML de bienvenida minimalista con colores del informe
            html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bienvenido a Informe Diario</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; padding: 50px 20px;">
        <tr>
            <td align="center">
                
                <!-- Container -->
                <table width="500" cellpadding="0" cellspacing="0" style="max-width: 500px; width: 100%; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 35px 40px; background-color: #0f172a; text-align: center;">
                            <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.025em;">
                                INFORME DIARIO
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            
                            <p style="margin: 0 0 20px 0; font-size: 17px; color: #1e293b; line-height: 1.6;">
                                Hola {nombre_destinatario},
                            </p>
                            
                            <p style="margin: 0 0 25px 0; font-size: 16px; color: #475569; line-height: 1.6;">
                                Tu cuenta ha sido creada exitosamente.
                            </p>
                            
                            <p style="margin: 0 0 30px 0; font-size: 16px; color: #475569; line-height: 1.6;">
                                <strong style="color: #1e293b;">Email:</strong> {email_destinatario}
                            </p>
                            
                            <p style="margin: 0 0 30px 0; font-size: 16px; color: #475569; line-height: 1.6;">
                                Ya puedes iniciar sesión en la plataforma.
                            </p>
                            
                            <p style="margin: 0; font-size: 17px; color: #1e293b; line-height: 1.6;">
                                ¡Bienvenido!
                            </p>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; background-color: #f8fafc; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-size: 13px; color: #64748b;">
                                © 2025 Informe Diario • Santiago, Chile
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
            </td>
        </tr>
    </table>
    
</body>
</html>
        """
        
        # Configuración del servidor SMTP
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = 'contacto@informediariochile.cl'  # Usar el email oficial
        smtp_password = os.environ.get('HOSTINGER_EMAIL_PASSWORD')
        
        if not smtp_password:
            print("❌ Error: HOSTINGER_EMAIL_PASSWORD no está configurado")
            return False
        
        # Enviar email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject  # Usar el subject que se determinó arriba
        msg['From'] = smtp_user
        msg['To'] = email_destinatario
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Enviar
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Correo de bienvenida enviado exitosamente a {email_destinatario}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando correo de bienvenida: {str(e)}")
        return False