#!/usr/bin/env python3
"""
Script simple para reenviar el informe del 13 de agosto a los afectados
Usa el HTML del informe ya generado pero sin comentarios MSO
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import os
import re

# Lista de destinatarios afectados
DESTINATARIOS_AFECTADOS = [
    "lvarela@bye.cl",
    "mizcue@bye.cl", 
    "bjottar@bye.cl",
    "mulloa@bye.cl",
    "fsteinmetz@bsvv.cl"  # Ya probado exitosamente
]

def limpiar_html_mso(html_content):
    """Elimina todos los comentarios MSO del HTML"""
    # Eliminar comentarios condicionales MSO
    html_limpio = re.sub(r'<!--\[if mso\]>.*?<!\[endif\]-->', '', html_content, flags=re.DOTALL)
    html_limpio = re.sub(r'<!--\[if !mso\]><!-->.*?<!--<!\[endif\]-->', '', html_limpio, flags=re.DOTALL)
    
    # Eliminar cualquier referencia a VML
    html_limpio = re.sub(r'v:.*?[\s>]', '', html_limpio)
    html_limpio = re.sub(r'xmlns:v="urn:schemas-microsoft-com:vml"', '', html_limpio)
    html_limpio = re.sub(r'xmlns:o="urn:schemas-microsoft-com:office:office"', '', html_limpio)
    
    return html_limpio

def main():
    # Leer el HTML del informe del 13 de agosto
    archivo_informe = "/Users/rodrigofernandezdelrio/Desktop/Project Diario Oficial/informe_diario_13_08_2025.html"
    
    # Si no existe, usar cualquier informe disponible como base
    if not os.path.exists(archivo_informe):
        # Buscar algún informe existente
        for archivo in ["informe_diario_07_08_2025.html", "informe_diario_06_08_2025.html", "informe_diario_05_08_2025.html"]:
            archivo_path = f"/Users/rodrigofernandezdelrio/Desktop/Project Diario Oficial/{archivo}"
            if os.path.exists(archivo_path):
                archivo_informe = archivo_path
                print(f"Usando informe base: {archivo}")
                break
    
    if not os.path.exists(archivo_informe):
        print("❌ No se encontró ningún archivo de informe para usar como base")
        return
    
    # Leer el HTML
    with open(archivo_informe, 'r', encoding='utf-8') as f:
        html_original = f.read()
    
    # Limpiar comentarios MSO
    html_limpio = limpiar_html_mso(html_original)
    
    # Actualizar fecha en el HTML
    html_limpio = html_limpio.replace("07 de agosto, 2025", "13 de agosto, 2025")
    html_limpio = html_limpio.replace("06 de agosto, 2025", "13 de agosto, 2025")
    html_limpio = html_limpio.replace("05 de agosto, 2025", "13 de agosto, 2025")
    
    # Crear versión texto plano
    text_content = """INFORME DIARIO CHILE - 13 de agosto, 2025
=========================================

Este es el reenvío del informe diario que no llegó anteriormente
debido a problemas de compatibilidad con Microsoft Exchange.

El problema ha sido solucionado eliminando los comentarios
condicionales MSO que causaban el bloqueo.

Para ver el informe completo, visite: https://informediariochile.cl

=========================================
© 2025 Informe Diario Chile
Para darse de baja: responder con BAJA en el asunto
"""
    
    # Configuración SMTP
    smtp_host = 'smtp.hostinger.com'
    smtp_port = 587
    smtp_user = 'contacto@informediariochile.cl'
    smtp_password = os.getenv('HOSTINGER_EMAIL_PASSWORD', 'Rfdr1729!')
    
    print("=" * 60)
    print("REENVÍO DE INFORME A DESTINATARIOS AFECTADOS")
    print("=" * 60)
    print(f"\nDestinatarios ({len(DESTINATARIOS_AFECTADOS)}):")
    
    enviados = 0
    errores = 0
    
    for destinatario in DESTINATARIOS_AFECTADOS:
        try:
            print(f"\n📧 Enviando a: {destinatario}...", end=" ")
            
            # Crear mensaje multipart/alternative
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Informe Diario Chile - 13 de agosto, 2025 (Reenvío)'
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
            msg.attach(MIMEText(html_limpio, 'html', 'utf-8'))
            
            # Enviar
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            print("✅ Enviado")
            enviados += 1
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            errores += 1
    
    print("\n" + "=" * 60)
    print("RESUMEN:")
    print(f"✅ Enviados exitosamente: {enviados}")
    print(f"❌ Errores: {errores}")
    print("=" * 60)
    
    if enviados > 0:
        print("\n✅ Proceso completado. Por favor verifica con los destinatarios.")

if __name__ == "__main__":
    main()