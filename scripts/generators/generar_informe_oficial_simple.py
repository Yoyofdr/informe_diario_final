#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generador de Informe Diario SIMPLIFICADO - Sin MSO, compatible con Microsoft Defender
Versión optimizada para máxima entregabilidad
"""

import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from datetime import datetime
import pytz
import logging

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
import django
django.setup()

from alerts.models import InformeDiarioCache, Destinatario
from alerts.scraper_diario_oficial import obtener_sumario_diario_oficial
from scripts.scrapers.scraper_cmf_mejorado import obtener_hechos_esenciales_dia
from alerts.scrapers.scraper_sii import obtener_publicaciones_sii_hoy
from alerts.cmf_criterios_profesionales import filtrar_hechos_profesional

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generar_texto_plano(diario_oficial, hechos_cmf, publicaciones_sii, fecha):
    """Genera versión texto plano del informe para multipart/alternative"""
    texto = f"""INFORME DIARIO CHILE - {fecha}
=========================================

DIARIO OFICIAL
--------------
"""
    
    # Normas Generales
    normas_generales = [p for p in diario_oficial.get('publicaciones_relevantes', []) 
                       if p.get('seccion') == 'Normas Generales'][:3]
    if normas_generales:
        texto += "\nNORMAS GENERALES:\n"
        for pub in normas_generales:
            texto += f"• {pub.get('titulo', '')}\n"
            texto += f"  {pub.get('resumen', '')[:100]}...\n\n"
    
    # CMF
    if hechos_cmf:
        texto += "\nHECHOS ESENCIALES CMF:\n"
        for hecho in hechos_cmf[:5]:
            texto += f"• {hecho.get('entidad', '')}: {hecho.get('titulo', '')}\n"
            texto += f"  {hecho.get('resumen', '')[:100]}...\n\n"
    
    # SII
    if publicaciones_sii:
        texto += "\nSERVICIO DE IMPUESTOS INTERNOS:\n"
        for pub in publicaciones_sii[:3]:
            texto += f"• {pub.get('tipo', '')}: {pub.get('titulo', '')}\n\n"
    
    texto += """
=========================================
Ver informe completo en: https://informediariochile.cl

Para darse de baja: responder con BAJA en el asunto
"""
    
    return texto

def generar_html_simple(diario_oficial, hechos_cmf, publicaciones_sii, fecha_formato):
    """Genera HTML simple sin comentarios MSO, optimizado para Microsoft Defender"""
    
    # Extraer publicaciones relevantes
    publicaciones_relevantes = diario_oficial.get('publicaciones_relevantes', [])
    
    # Clasificar por sección
    normas_generales = [p for p in publicaciones_relevantes if p.get('seccion') == 'Normas Generales'][:3]
    normas_particulares = [p for p in publicaciones_relevantes if p.get('seccion') == 'Normas Particulares'][:3]
    avisos_destacados = [p for p in publicaciones_relevantes if p.get('seccion') == 'Avisos Destacados'][:3]
    
    # HTML simple sin comentarios condicionales
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe Diario • {fecha_formato}</title>
    <style type="text/css">
        /* Reset básico */
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }}
        
        /* Estilos responsive básicos */
        @media screen and (max-width: 600px) {{
            .wrapper {{ width: 100% !important; max-width: 100% !important; }}
            .section-padding {{ padding: 16px !important; }}
            h1 {{ font-size: 24px !important; }}
            h2 {{ font-size: 16px !important; }}
            h3 {{ font-size: 14px !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8fafc;">
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                
                <!-- Wrapper principal -->
                <table class="wrapper" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; background-color: #ffffff;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0 0 8px 0; font-size: 26px; font-weight: 700; color: #ffffff;">
                                Informe Diario
                            </h1>
                            <p style="margin: 0; font-size: 14px; font-weight: 500; color: #ffffff;">
                                {fecha_formato}
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 30px;">"""
    
    # NORMAS GENERALES
    if normas_generales:
        html += """
                            <!-- NORMAS GENERALES -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px;">
                                <tr>
                                    <td>
                                        <h2 style="margin: 0 0 15px 0; font-size: 18px; font-weight: 600; color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                                            NORMAS GENERALES
                                        </h2>
                                    </td>
                                </tr>"""
        
        for pub in normas_generales:
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 15px;">
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 18px; border-left: 3px solid #6b7280;">
                                                    <h3 style="margin: 0 0 10px 0; font-size: 15px; font-weight: 600; color: #1e293b;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 12px 0; font-size: 13px; color: #64748b; line-height: 1.5;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #6b7280; padding: 10px 20px;">
                                                                <a href="{pub.get('url_pdf', '#')}" style="color: #ffffff; font-size: 13px; font-weight: 500; text-decoration: none;">
                                                                    Ver documento
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # HECHOS ESENCIALES CMF
    if hechos_cmf:
        html += """
                            <!-- HECHOS ESENCIALES CMF -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px;">
                                <tr>
                                    <td>
                                        <h2 style="margin: 0 0 15px 0; font-size: 18px; font-weight: 600; color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                                            HECHOS ESENCIALES - CMF
                                        </h2>
                                    </td>
                                </tr>"""
        
        for hecho in hechos_cmf[:5]:
            url_hecho = f"https://www.cmfchile.cl/institucional/mercados/entidad.php?mercado=V&rut={hecho.get('rut', '')}&grupo=&tipoentidad=RVEMI&row=&vig=VI&control=svs&pestania=5"
            
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 15px;">
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 18px; border-left: 3px solid #7c3aed;">
                                                    <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #7c3aed;">
                                                        {hecho.get('entidad', '')}
                                                    </h3>
                                                    <div style="margin: 0 0 10px 0; font-size: 14px; font-weight: 600; color: #1e293b;">
                                                        {hecho.get('titulo', hecho.get('materia', ''))}
                                                    </div>
                                                    <p style="margin: 0 0 12px 0; font-size: 13px; color: #64748b; line-height: 1.5;">
                                                        {hecho.get('resumen', '')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #7c3aed; padding: 10px 20px;">
                                                                <a href="{url_hecho}" style="color: #ffffff; font-size: 13px; font-weight: 500; text-decoration: none;">
                                                                    Ver hecho esencial
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # SERVICIO DE IMPUESTOS INTERNOS
    if publicaciones_sii:
        html += """
                            <!-- SERVICIO DE IMPUESTOS INTERNOS -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px;">
                                <tr>
                                    <td>
                                        <h2 style="margin: 0 0 15px 0; font-size: 18px; font-weight: 600; color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                                            SERVICIO DE IMPUESTOS INTERNOS
                                        </h2>
                                    </td>
                                </tr>"""
        
        for pub in publicaciones_sii[:3]:
            url_documento = pub.get('url', '#')
            titulo_completo = f"{pub.get('tipo', '')} {pub.get('numero', '')}"
            
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 15px;">
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 18px; border-left: 3px solid #2563eb;">
                                                    <h3 style="margin: 0 0 10px 0; font-size: 15px; font-weight: 600; color: #1e293b;">
                                                        {titulo_completo}
                                                    </h3>
                                                    <p style="margin: 0 0 12px 0; font-size: 13px; color: #64748b; line-height: 1.5;">
                                                        {pub.get('titulo', 'Sin descripción disponible')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #2563eb; padding: 10px 20px;">
                                                                <a href="{url_documento}" style="color: #ffffff; font-size: 13px; font-weight: 500; text-decoration: none;">
                                                                    Ver documento SII
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # Footer
    html += """
                            <!-- Footer -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                                <tr>
                                    <td style="text-align: center;">
                                        <p style="margin: 0 0 8px 0; font-size: 12px; color: #94a3b8;">
                                            © 2025 Informe Diario Chile. Todos los derechos reservados.
                                        </p>
                                        <p style="margin: 0 0 8px 0; font-size: 12px; color: #94a3b8;">
                                            <a href="https://informediariochile.cl" style="color: #7c3aed; text-decoration: none;">Ver en navegador</a> | 
                                            <a href="mailto:bajas@informediariochile.cl?subject=BAJA" style="color: #7c3aed; text-decoration: none;">Darse de baja</a>
                                        </p>
                                        <p style="margin: 0; font-size: 11px; color: #cbd5e1;">
                                            Has recibido este email porque estás suscrito a nuestro servicio de informes diarios.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return html

def enviar_informe_oficial(fecha=None):
    """Función principal para generar y enviar el informe"""
    chile_tz = pytz.timezone('America/Santiago')
    
    if fecha:
        fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
        fecha_obj = chile_tz.localize(fecha_obj)
    else:
        fecha_obj = datetime.now(chile_tz)
    
    fecha_formato = fecha_obj.strftime("%d de %B, %Y").replace(
        'January', 'enero').replace('February', 'febrero').replace(
        'March', 'marzo').replace('April', 'abril').replace(
        'May', 'mayo').replace('June', 'junio').replace(
        'July', 'julio').replace('August', 'agosto').replace(
        'September', 'septiembre').replace('October', 'octubre').replace(
        'November', 'noviembre').replace('December', 'diciembre')
    
    fecha_str = fecha_obj.strftime("%d-%m-%Y")
    fecha_db = fecha_obj.strftime("%Y-%m-%d")
    
    logger.info(f"📅 Generando informe para: {fecha_formato}")
    
    # Verificar caché
    try:
        cache = InformeDiarioCache.objects.get(fecha=fecha_db)
        if cache.contenido_html:
            logger.info("✅ Usando informe desde caché")
            html_content = cache.contenido_html
            # Generar texto plano desde el HTML cacheado (simplificado)
            text_content = f"""INFORME DIARIO CHILE - {fecha_formato}
=========================================

Este es un resumen del informe diario.
Para ver el informe completo, visite: https://informediariochile.cl

Para darse de baja: responder con BAJA en el asunto
"""
    except:
        # Obtener datos
        logger.info("🔄 Generando nuevo informe...")
        diario_oficial = obtener_sumario_diario_oficial(fecha_str)
        hechos_cmf = filtrar_hechos_profesional(obtener_hechos_esenciales_dia(fecha_str))
        publicaciones_sii = obtener_publicaciones_sii_hoy(fecha_str)
        
        # Generar HTML y texto
        html_content = generar_html_simple(diario_oficial, hechos_cmf, publicaciones_sii, fecha_formato)
        text_content = generar_texto_plano(diario_oficial, hechos_cmf, publicaciones_sii, fecha_formato)
        
        # Guardar en caché
        InformeDiarioCache.objects.update_or_create(
            fecha=fecha_db,
            defaults={'contenido_html': html_content}
        )
    
    # Obtener destinatarios
    destinatarios_prueba = os.getenv('INFORME_DESTINATARIOS_PRUEBA', '')
    if destinatarios_prueba:
        destinatarios = [email.strip() for email in destinatarios_prueba.split(',')]
        logger.info(f"MODO PRUEBA: enviando a {len(destinatarios)} destinatarios")
    else:
        destinatarios = list(Destinatario.objects.values_list('email', flat=True))
        logger.info(f"📧 Preparando envío a {len(destinatarios)} destinatarios")
    
    # Configuración SMTP
    smtp_host = os.getenv('EMAIL_HOST', 'smtp.hostinger.com')
    smtp_port = int(os.getenv('EMAIL_PORT', 587))
    smtp_user = os.getenv('EMAIL_HOST_USER', 'contacto@informediariochile.cl')
    smtp_password = os.getenv('EMAIL_HOST_PASSWORD')
    
    if not smtp_password:
        logger.error("❌ No se encontró EMAIL_HOST_PASSWORD")
        return
    
    # Enviar emails
    enviados = 0
    errores = 0
    
    for destinatario in destinatarios:
        try:
            # Crear mensaje multipart/alternative
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Informe Diario Chile - {fecha_formato}'
            msg['From'] = smtp_user
            msg['To'] = destinatario
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain='informediariochile.cl')
            
            # Headers de reputación
            msg['List-Unsubscribe'] = f'<mailto:bajas@informediariochile.cl?subject=BAJA>, <https://informediariochile.cl/unsubscribe?email={destinatario}>'
            msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
            msg['Auto-Submitted'] = 'auto-generated'
            msg['Precedence'] = 'bulk'
            
            # Adjuntar partes texto y HTML
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Enviar
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            enviados += 1
            logger.info(f"✅ Enviado a: {destinatario}")
            
        except Exception as e:
            errores += 1
            logger.error(f"❌ Error enviando a {destinatario}: {str(e)}")
    
    # Resumen
    logger.info(f"""
📊 RESUMEN DE ENVÍO:
✅ Enviados exitosamente: {enviados}
❌ Errores: {errores}
📧 Total destinatarios: {len(destinatarios)}
""")
    
    if enviados > 0:
        logger.info(f"✅ Informes enviados exitosamente para {fecha_str}")
    else:
        logger.error(f"❌ No se pudo enviar ningún informe para {fecha_str}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fecha_param = sys.argv[1]
        enviar_informe_oficial(fecha_param)
    else:
        enviar_informe_oficial()