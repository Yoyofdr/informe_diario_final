#!/usr/bin/env python3
"""
Script de prueba para enviar informe con HTML simplificado
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import os

def enviar_prueba():
    """Enviar email de prueba con HTML simplificado"""
    
    # HTML simple sin comentarios MSO
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Informe Diario de Prueba</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8fafc;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center" style="padding: 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff;">
                    <tr>
                        <td style="background-color: #0f172a; padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 26px;">
                                Informe Diario - PRUEBA
                            </h1>
                            <p style="margin: 8px 0 0 0; color: #ffffff; font-size: 14px;">
                                13 de agosto, 2025
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="margin: 0 0 15px 0; font-size: 18px; color: #1e293b;">
                                PRUEBA DE ENTREGABILIDAD
                            </h2>
                            <p style="margin: 0 0 20px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                Este es un email de prueba con HTML simplificado sin comentarios MSO.
                                El objetivo es verificar que llega correctamente a los buzones corporativos
                                que usan Microsoft Exchange/Outlook.
                            </p>
                            <p style="margin: 0 0 20px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                <strong>Cambios realizados:</strong><br>
                                • Eliminados todos los comentarios condicionales MSO<br>
                                • HTML simple con tablas básicas<br>
                                • Agregado multipart/alternative con texto plano<br>
                                • Headers de reputación incluidos<br>
                                • Tamaño reducido a menos de 50KB
                            </p>
                            <table cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="background-color: #6b7280; padding: 12px 24px;">
                                        <a href="https://informediariochile.cl" style="color: #ffffff; text-decoration: none; font-weight: 500;">
                                            Ver sitio web
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                                © 2025 Informe Diario Chile - Prueba de entregabilidad
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    # Texto plano
    text_content = """INFORME DIARIO - PRUEBA DE ENTREGABILIDAD
=========================================

Este es un email de prueba con HTML simplificado sin comentarios MSO.

El objetivo es verificar que llega correctamente a los buzones corporativos
que usan Microsoft Exchange/Outlook.

Cambios realizados:
• Eliminados todos los comentarios condicionales MSO
• HTML simple con tablas básicas
• Agregado multipart/alternative con texto plano
• Headers de reputación incluidos
• Tamaño reducido a menos de 50KB

=========================================
© 2025 Informe Diario Chile
"""
    
    # Configuración SMTP
    smtp_host = os.getenv('EMAIL_HOST', 'smtp.hostinger.com')
    smtp_port = int(os.getenv('EMAIL_PORT', 587))
    smtp_user = os.getenv('EMAIL_HOST_USER', 'contacto@informediariochile.cl')
    smtp_password = os.getenv('HOSTINGER_EMAIL_PASSWORD')
    
    if not smtp_password:
        print("❌ No se encontró HOSTINGER_EMAIL_PASSWORD")
        return
    
    # Destinatario de prueba
    destinatario = "fsteinmetz@bsvv.cl"
    
    # Crear mensaje multipart/alternative
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'PRUEBA: Informe Diario Simplificado - 13 agosto 2025'
    msg['From'] = smtp_user
    msg['To'] = destinatario
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain='informediariochile.cl')
    
    # Headers de reputación
    msg['List-Unsubscribe'] = f'<mailto:bajas@informediariochile.cl?subject=BAJA>'
    msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
    msg['Auto-Submitted'] = 'auto-generated'
    msg['Precedence'] = 'bulk'
    
    # Adjuntar partes texto y HTML
    msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    # Enviar
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.set_debuglevel(1)  # Para ver el diálogo SMTP
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Email de prueba enviado exitosamente a: {destinatario}")
        print("\nPor favor, verifica con el destinatario si llegó al buzón principal.")
        print("Si llega correctamente, podemos proceder con el despliegue completo.")
        
    except Exception as e:
        print(f"❌ Error enviando email: {str(e)}")

if __name__ == "__main__":
    enviar_prueba()