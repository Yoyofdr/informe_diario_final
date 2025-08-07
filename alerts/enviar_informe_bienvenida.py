"""
Función para enviar automáticamente el informe integrado completo
(Diario Oficial + CMF + SII) a nuevos usuarios cuando se registran
"""
import os
import sys
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import subprocess
from django.conf import settings


def enviar_informe_bienvenida(email_destinatario, nombre_destinatario):
    """
    Envía el informe integrado completo del día actual a un nuevo usuario
    
    Args:
        email_destinatario (str): Email del nuevo usuario
        nombre_destinatario (str): Nombre completo del nuevo usuario
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    
    # Verificar si es domingo
    if datetime.now().weekday() == 6:
        print(f"=== NO SE ENVÍA INFORME A {email_destinatario} PORQUE ES DOMINGO ===\n")
        # Enviar correo de bienvenida sin informe
        return enviar_correo_bienvenida_sin_informe(email_destinatario, nombre_destinatario)
    
    fecha = datetime.now().strftime("%d-%m-%Y")
    
    print(f"=== ENVIANDO INFORME INTEGRADO A NUEVO USUARIO {email_destinatario} ===\n")
    
    try:
        # Cambiar temporalmente el destinatario en las variables de entorno
        original_email = os.environ.get('INFORME_DESTINATARIO_TEMP', 'rfernandezdelrio@uc.cl')
        os.environ['INFORME_DESTINATARIO_TEMP'] = email_destinatario
        os.environ['INFORME_ES_BIENVENIDA'] = 'true'
        os.environ['INFORME_NOMBRE_TEMP'] = nombre_destinatario
        
        # Buscar el script integrado mejorado
        script_path = None
        possible_paths = [
            os.path.join(settings.BASE_DIR, 'repo_limpio', 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py'),
            os.path.join(settings.BASE_DIR, 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py'),
            os.path.join(settings.BASE_DIR, '..', 'repo_limpio', 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py'),
            os.path.join(settings.BASE_DIR, 'repo_clean', 'generar_informe_oficial_integrado_mejorado.py'),
            os.path.join(settings.BASE_DIR, 'generar_informe_oficial_integrado_mejorado.py'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                script_path = path
                break
        
        if not script_path:
            print("❌ Error: No se encontró el script generar_informe_oficial_integrado_mejorado.py")
            return False
        
        print(f"Usando script: {script_path}")
        
        # Ejecutar el script integrado
        result = subprocess.run(
            [sys.executable, script_path, fecha],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(script_path)
        )
        
        # Restaurar el email original
        os.environ['INFORME_DESTINATARIO_TEMP'] = original_email
        os.environ['INFORME_ES_BIENVENIDA'] = 'false'
        os.environ.pop('INFORME_NOMBRE_TEMP', None)
        
        if result.returncode == 0:
            print(f"\n✅ INFORME INTEGRADO ENVIADO EXITOSAMENTE")
            print(f"   Para: {email_destinatario}")
            print(f"   Incluye: Diario Oficial + CMF + SII")
            return True
        else:
            print(f"\n❌ Error ejecutando el script: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error enviando informe de bienvenida: {str(e)}")
        # Restaurar el email original en caso de error
        if 'original_email' in locals():
            os.environ['INFORME_DESTINATARIO_TEMP'] = original_email
            os.environ['INFORME_ES_BIENVENIDA'] = 'false'
            os.environ.pop('INFORME_NOMBRE_TEMP', None)
        return False


def enviar_correo_bienvenida_sin_informe(email_destinatario, nombre_destinatario):
    """
    Envía solo un correo de bienvenida sin el informe (para domingos)
    """
    try:
        # Formatear fecha actual
        fecha_obj = datetime.now()
        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        fecha_formato = f"{fecha_obj.day} de {meses[fecha_obj.month]}, {fecha_obj.year}"
        
        # Crear mensaje HTML de bienvenida
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    padding: 40px;
                }}
                h1 {{
                    color: #0369a1;
                    margin-bottom: 20px;
                }}
                p {{
                    color: #333;
                    line-height: 1.6;
                    margin-bottom: 15px;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e5e5;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>¡Bienvenido a Informe Diario, {nombre_destinatario}!</h1>
                
                <p>
                    Gracias por registrarte en nuestro servicio de informes diarios.
                </p>
                
                <p>
                    A partir de mañana lunes, recibirás cada día (de lunes a sábado) a las 9:00 AM 
                    un resumen con lo más relevante del:
                </p>
                
                <ul>
                    <li><strong>Diario Oficial:</strong> Normas generales, particulares y avisos destacados</li>
                    <li><strong>CMF:</strong> Hechos esenciales del mercado financiero</li>
                    <li><strong>SII:</strong> Publicaciones y normativas tributarias</li>
                </ul>
                
                <p>
                    <em>Nota: No enviamos informes los domingos, por lo que hoy no recibirás el informe diario. 
                    Tu primer informe llegará el próximo día hábil.</em>
                </p>
                
                <div class="footer">
                    <p>
                        Si tienes alguna pregunta o necesitas ayuda, no dudes en contactarnos.
                    </p>
                    <p>
                        Saludos cordiales,<br>
                        El equipo de Informe Diario
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Enviar email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"¡Bienvenido a Informe Diario!"
        msg['From'] = "rodrigo@carvuk.com"
        msg['To'] = email_destinatario
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Enviar
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("rodrigo@carvuk.com", "swqjlcwjaoooyzcb")
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Correo de bienvenida enviado a {email_destinatario} (sin informe por ser domingo)")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando correo de bienvenida: {str(e)}")
        return False


def enviar_informe_bienvenida_simple(email_destinatario, nombre_destinatario):
    """
    Versión alternativa que envía directamente sin cambiar variables de entorno
    """
    fecha = datetime.now().strftime("%d-%m-%Y")
    
    try:
        # Importar las funciones necesarias del script integrado
        sys.path.insert(0, os.path.join(settings.BASE_DIR, 'repo_clean'))
        from generar_informe_oficial_integrado_mejorado import (
            generar_html_informe, 
            obtener_sumario_diario_oficial, 
            obtener_hechos_cmf_dia, 
            obtener_publicaciones_sii_dia
        )
        
        # Obtener datos de las 3 fuentes
        print("Obteniendo datos del Diario Oficial...")
        resultado_diario = obtener_sumario_diario_oficial(fecha)
        
        print("Obteniendo hechos CMF...")
        hechos_cmf = obtener_hechos_cmf_dia(fecha)
        
        print("Obteniendo publicaciones SII...")
        publicaciones_sii = obtener_publicaciones_sii_dia(fecha)
        
        # Generar HTML del informe
        print("Generando informe integrado...")
        html = generar_html_informe(fecha, resultado_diario, hechos_cmf, publicaciones_sii)
        
        # Formatear fecha para el asunto
        fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        fecha_formato = f"{fecha_obj.day} de {meses[fecha_obj.month]}, {fecha_obj.year}"
        
        # Enviar email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Bienvenido a Informe Diario • {fecha_formato}"
        msg['From'] = "rodrigo@carvuk.com"
        msg['To'] = email_destinatario
        
        # Agregar mensaje personalizado de bienvenida al inicio del HTML
        welcome_html = f"""
        <div style="background-color: #f0f9ff; border: 1px solid #0369a1; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
            <h2 style="color: #0369a1; margin: 0 0 10px 0;">¡Bienvenido {nombre_destinatario}!</h2>
            <p style="color: #0c4a6e; margin: 0;">
                Gracias por registrarte en Informe Diario. A partir de ahora recibirás cada mañana 
                un resumen con lo más relevante del Diario Oficial, CMF y SII.
            </p>
            <p style="color: #0c4a6e; margin: 10px 0 0 0;">
                A continuación encontrarás el informe de hoy:
            </p>
        </div>
        """
        
        # Insertar el mensaje de bienvenida en el HTML
        html_with_welcome = html.replace('<body style="', welcome_html + '<body style="')
        
        html_part = MIMEText(html_with_welcome, 'html')
        msg.attach(html_part)
        
        # Enviar
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("rodrigo@carvuk.com", "swqjlcwjaoooyzcb")
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Informe integrado enviado a {email_destinatario}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False