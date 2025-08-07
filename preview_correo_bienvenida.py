#!/usr/bin/env python3
"""
Script para generar preview del correo de bienvenida
"""
import os
import sys
import django
from datetime import datetime
from pathlib import Path
import pytz

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

# Generar preview
if __name__ == "__main__":
    # Formatear fecha actual
    chile_tz = pytz.timezone('America/Santiago')
    fecha_obj = datetime.now(chile_tz)
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    fecha_formato = f"{fecha_obj.day} de {meses[fecha_obj.month]}, {fecha_obj.year}"
    
    # Determinar cuándo recibirá su primer informe
    dia_semana = fecha_obj.weekday()
    if dia_semana == 6:  # Domingo
        primer_informe = "mañana lunes"
    elif dia_semana == 5:  # Sábado
        primer_informe = "el lunes"
    else:
        primer_informe = "mañana"
    
    nombre_destinatario = "Rodrigo"
    
    nombre_destinatario = "Rodrigo"
    email_destinatario = "rodrigo@carvuk.com"
    
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
                                Hola {nombre_destinatario}
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
    
    # Guardar archivo
    filename = "preview_correo_bienvenida.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Preview guardado en: {filename}")
    print(f"📧 Abre el archivo en tu navegador para ver cómo se ve el correo")