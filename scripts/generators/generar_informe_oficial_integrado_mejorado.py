#!/usr/bin/env python3
"""
Generador de informe oficial integrado mejorado
Incluye actualización automática de enlaces CMF
"""

import json
import os
import sys
import django
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import logging
from pathlib import Path
import pytz

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

# Importar scrapers
from alerts.scraper_diario_oficial import obtener_sumario_diario_oficial
from scripts.scrapers.scraper_cmf_mejorado import ScraperCMFMejorado
from alerts.cmf_criterios_profesionales import filtrar_hechos_profesional, get_icono_categoria
from alerts.scraper_sii import obtener_circulares_sii, obtener_resoluciones_exentas_sii, obtener_jurisprudencia_administrativa_sii
from alerts.cmf_resumenes_ai import generar_resumen_cmf
from alerts.utils.cache_informe import CacheInformeDiario

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def formatear_fecha_espanol(fecha_obj, con_coma=True, mes_mayuscula=False):
    """
    Formatea una fecha en español con el mes en minúscula por defecto
    Ej: 04 de agosto, 2025 (con_coma=True)
    Ej: 04 de agosto de 2025 (con_coma=False)
    """
    meses = {
        'January': 'enero', 'February': 'febrero', 'March': 'marzo',
        'April': 'abril', 'May': 'mayo', 'June': 'junio',
        'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
        'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
    }
    
    # Obtener la fecha en inglés
    if con_coma:
        fecha_str = fecha_obj.strftime("%d de %B, %Y")
    else:
        fecha_str = fecha_obj.strftime("%d de %B de %Y")
    
    # Reemplazar el mes en inglés por el español
    for mes_ingles, mes_espanol in meses.items():
        if mes_mayuscula:
            mes_espanol = mes_espanol.capitalize()
        fecha_str = fecha_str.replace(mes_ingles, mes_espanol)
    
    return fecha_str

def obtener_publicaciones_sii_dia(fecha):
    """
    Obtiene las publicaciones del SII del día anterior
    """
    try:
        # Obtener fecha del día anterior
        fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
        fecha_anterior = fecha_obj - timedelta(days=1)
        fecha_anterior_str = fecha_anterior.strftime("%d-%m-%Y")
        
        year = fecha_anterior.year
        
        publicaciones = []
        
        # Usar la función de novedades tributarias para obtener solo del día anterior
        try:
            from alerts.scraper_sii import obtener_novedades_tributarias_sii
            resultado_sii = obtener_novedades_tributarias_sii(fecha_referencia=fecha_anterior, dias_atras=1)
            
            # La función devuelve un diccionario con 'circulares' y 'resoluciones_exentas'
            if isinstance(resultado_sii, dict):
                # Solo procesar si realmente son del día anterior
                # Verificar si las publicaciones son del día que buscamos
                fecha_buscada_str = formatear_fecha_espanol(fecha_anterior, con_coma=False, mes_mayuscula=True)
                
                # Procesar circulares - solo si son del día anterior
                for circular in resultado_sii.get('circulares', []):
                    fecha_pub = circular.get('fecha', '')
                    # Solo incluir si la fecha coincide con el día anterior
                    if fecha_pub and fecha_buscada_str.lower() in fecha_pub.lower():
                        publicaciones.append({
                            'tipo': 'Circular',
                            'numero': circular.get('numero', ''),
                            'titulo': circular.get('titulo', ''),
                            'fecha_publicacion': fecha_pub,
                            'url': circular.get('url_pdf', circular.get('url', ''))
                        })
                
                # Procesar resoluciones exentas - solo si son del día anterior
                for resolucion in resultado_sii.get('resoluciones_exentas', []):
                    fecha_pub = resolucion.get('fecha', '')
                    # Solo incluir si la fecha coincide con el día anterior
                    if fecha_pub and fecha_buscada_str.lower() in fecha_pub.lower():
                        publicaciones.append({
                            'tipo': 'Resolución Exenta',
                            'numero': resolucion.get('numero', ''),
                            'titulo': resolucion.get('titulo', ''),
                            'fecha_publicacion': fecha_pub,
                            'url': resolucion.get('url_pdf', resolucion.get('url', ''))
                        })
                    
                # Procesar jurisprudencia si existe - solo si es del día anterior
                for juris in resultado_sii.get('jurisprudencia_administrativa', []):
                    fecha_pub = juris.get('fecha', '')
                    if fecha_pub and fecha_buscada_str.lower() in fecha_pub.lower():
                        publicaciones.append({
                            'tipo': 'Jurisprudencia',
                            'numero': juris.get('numero', ''),
                            'titulo': juris.get('titulo', ''),
                            'fecha_publicacion': fecha_pub,
                            'url': juris.get('url_pdf', juris.get('url', ''))
                        })
        except Exception as e:
            logger.error(f"Error obteniendo novedades SII: {e}")
            # NO usar fallback - si no hay del día anterior, no mostrar nada
        
        return publicaciones[:5]  # Retornar máximo 5 publicaciones
        
    except Exception as e:
        logger.error(f"Error general obteniendo publicaciones SII: {e}")
        return []

def obtener_hechos_cmf_dia(fecha):
    """
    Obtiene los hechos CMF del día anterior al especificado
    Primero actualiza los enlaces y luego los lee del JSON
    Aplica filtrado profesional según criterios de Kampala
    """
    # Obtener fecha del día anterior
    fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
    fecha_anterior = fecha_obj - timedelta(days=1)
    fecha_anterior_str = fecha_anterior.strftime("%d-%m-%Y")
    
    # Actualizar enlaces CMF para el día anterior
    logger.info(f"Actualizando enlaces CMF para {fecha_anterior_str}")
    scraper = ScraperCMFMejorado()
    
    # Convertir fecha al formato que espera el scraper (DD/MM/YYYY)
    fecha_scraper = fecha_anterior.strftime("%d/%m/%Y")
    
    # Actualizar JSON con enlaces correctos
    scraper.actualizar_json_hechos(fecha_scraper)
    
    # Leer hechos del JSON actualizado
    try:
        json_path = BASE_DIR / 'data' / 'hechos_cmf_selenium_reales.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            todos_hechos = datos.get('hechos', [])
        
        # Filtrar por fecha del día anterior
        hechos_dia = [h for h in todos_hechos if h.get('fecha') == fecha_anterior_str]
        
        logger.info(f"Hechos CMF encontrados para {fecha_anterior_str}: {len(hechos_dia)}")
        
        # Aplicar filtrado profesional (máx 12, criterios de relevancia)
        hechos_filtrados = filtrar_hechos_profesional(hechos_dia, max_hechos=12)
        
        logger.info(f"Hechos después del filtrado profesional: {len(hechos_filtrados)}")
        
        # Generar resúmenes con IA para cada hecho
        logger.info("Generando resúmenes con IA para hechos CMF...")
        for hecho in hechos_filtrados:
            entidad = hecho.get('entidad', '')
            materia = hecho.get('materia', hecho.get('titulo', ''))
            
            # Generar resumen con IA
            resumen_ai = generar_resumen_cmf(entidad, materia)
            if resumen_ai:
                hecho['resumen'] = resumen_ai
                logger.info(f"✅ Resumen generado para {entidad}")
            else:
                # Mantener el resumen existente si falla la IA
                logger.warning(f"⚠️ No se pudo generar resumen AI para {entidad}")
        
        return hechos_filtrados
        
    except Exception as e:
        logger.error(f"Error al leer hechos CMF: {str(e)}")
        return []

def generar_informe_oficial(fecha=None):
    """
    Genera y envía el informe oficial del día
    """
    if not fecha:
        # Usar timezone de Chile
        chile_tz = pytz.timezone('America/Santiago')
        fecha = datetime.now(chile_tz).strftime("%d-%m-%Y")
    
    logger.info(f"Generando informe para {fecha}")
    
    # 1. Obtener datos del Diario Oficial
    logger.info("Obteniendo datos del Diario Oficial...")
    resultado_diario = obtener_sumario_diario_oficial(fecha)
    
    # 2. Obtener hechos CMF (con actualización de enlaces)
    logger.info("Obteniendo hechos CMF...")
    hechos_cmf = obtener_hechos_cmf_dia(fecha)
    
    # 3. Obtener publicaciones del SII
    logger.info("Obteniendo publicaciones del SII...")
    try:
        publicaciones_sii = obtener_publicaciones_sii_dia(fecha)
    except Exception as e:
        logger.error(f"Error obteniendo SII: {e}")
        publicaciones_sii = []
    
    # 4. Generar HTML del informe
    html = generar_html_informe(fecha, resultado_diario, hechos_cmf, publicaciones_sii)
    
    # 4.5 Guardar en caché de base de datos
    try:
        cache = CacheInformeDiario()
        fecha_obj = datetime.strptime(fecha, "%d-%m-%Y").date()
        cache.guardar_informe(html, fecha_obj)
        logger.info("Informe guardado en caché de base de datos")
    except Exception as e:
        logger.error(f"Error guardando en caché: {e}")
    
    # 4. Guardar copia local
    filename = f"informe_diario_{fecha.replace('-', '_')}.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info(f"Informe guardado en: {filename}")
    
    # 5. Enviar por email
    enviar_informe_email(html, fecha)
    
    return True

def generar_html_informe(fecha, resultado_diario, hechos_cmf, publicaciones_sii=None):
    """
    Genera el HTML del informe con el diseño aprobado
    """
    # Formatear fecha
    fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
    fecha_formato = formatear_fecha_espanol(fecha_obj)
    
    # Obtener publicaciones del Diario Oficial
    publicaciones = resultado_diario.get('publicaciones', [])
    normas_generales = [p for p in publicaciones if p.get('seccion', '').upper() == 'NORMAS GENERALES']
    normas_particulares = [p for p in publicaciones if p.get('seccion', '').upper() == 'NORMAS PARTICULARES']
    avisos_destacados = [p for p in publicaciones if p.get('seccion', '').upper() == 'AVISOS DESTACADOS']
    
    # Si no hay sección, usar todas las publicaciones como normas generales
    if not normas_generales and not normas_particulares and not avisos_destacados:
        normas_generales = publicaciones
    
    # Valores de monedas
    valores_monedas = resultado_diario.get('valores_monedas', {})
    
    html = f"""<!DOCTYPE html>
<html lang="es" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe Diario • {fecha}</title>
    <!--[if mso]>
    <xml>
        <o:OfficeDocumentSettings>
            <o:AllowPNG/>
            <o:PixelsPerInch>96</o:PixelsPerInch>
        </o:OfficeDocumentSettings>
    </xml>
    <![endif]-->
    <style>
        @media screen and (max-width: 600px) {{
            /* Ajustes para móviles */
            .wrapper {{ width: 100% !important; }}
            .content-padding {{ padding: 16px !important; }}
            .header-padding {{ padding: 32px 16px !important; }}
            .section-padding {{ padding: 16px !important; }}
            h1 {{ font-size: 24px !important; }}
            h2 {{ font-size: 16px !important; }}
            h3 {{ font-size: 14px !important; }}
            p, a, li {{ font-size: 14px !important; }}
            .small-text {{ font-size: 12px !important; }}
            .button {{ padding: 12px 16px !important; }}
            .mobile-block {{ display: block !important; width: 100% !important; margin-bottom: 8px !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc; color: #1e293b; line-height: 1.6;">
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                
                <!-- Wrapper -->
                <table class="wrapper" width="672" cellpadding="0" cellspacing="0" style="max-width: 672px; width: 100%; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td class="header-padding" style="background-color: #0f172a; padding: 48px 32px; text-align: center;">
                            <h1 style="margin: 0 0 8px 0; font-size: 28px; font-weight: 700; color: #ffffff; letter-spacing: -0.025em;">
                                Informe Diario
                            </h1>
                            <p style="margin: 0; font-size: 14px; font-weight: 500;">
                                <span style="color: #ffffff !important; text-decoration: none !important;">{fecha_formato}</span>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td class="content-padding" style="padding: 32px;">"""
    
    # Agregar mensaje de bienvenida si aplica
    es_bienvenida = os.getenv('INFORME_ES_BIENVENIDA', 'false') == 'true'
    if es_bienvenida:
        nombre_destinatario = os.getenv('INFORME_NOMBRE_TEMP', '')
        html += f"""
                            <!-- MENSAJE DE BIENVENIDA -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; padding: 24px;">
                                        <h2 style="margin: 0 0 12px 0; font-size: 20px; font-weight: 600; color: #059669;">
                                            ¡Bienvenido a Informe Diario{', ' + nombre_destinatario if nombre_destinatario else ''}!
                                        </h2>
                                        <p style="margin: 0 0 16px 0; font-size: 14px; color: #047857; line-height: 1.6;">
                                            Este es un ejemplo del informe integrado que recibirás diariamente. 
                                            Incluye información relevante de las 3 fuentes oficiales:
                                        </p>
                                        <ul style="margin: 0 0 16px 0; padding-left: 20px; color: #047857; font-size: 14px;">
                                            <li style="margin-bottom: 8px;"><strong>Diario Oficial:</strong> Normativas y avisos relevantes</li>
                                            <li style="margin-bottom: 8px;"><strong>CMF:</strong> Hechos esenciales del mercado financiero</li>
                                            <li style="margin-bottom: 8px;"><strong>SII:</strong> Circulares y resoluciones tributarias</li>
                                        </ul>
                                        <p style="margin: 0; font-size: 14px; color: #047857;">
                                            A partir de mañana, recibirás este informe todos los días hábiles a las 9:00 AM.
                                        </p>
                                    </td>
                                </tr>
                            </table>"""
    
    # Sección Diario Oficial
    if normas_generales:
        html += """
                            <!-- NORMAS GENERALES (DIARIO OFICIAL) -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eff6ff;">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 2px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        NORMAS GENERALES
                                                    </h2>
                                                    <p style="margin: 0; font-size: 14px; color: #6b7280;">
                                                        Leyes, decretos supremos y resoluciones de alcance general
                                                    </p>
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        for pub in normas_generales[:3]:  # Top 3
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <!--[if mso]>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 3px 0 0 0; background-color: #6b7280;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff;">
                                                        <tr>
                                                            <td class="section-padding" style="padding: 24px;">
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td class="section-padding" style="padding: 24px; border-top: 3px solid #6b7280; border-radius: 12px 12px 0 0; -webkit-border-radius: 12px 12px 0 0; -moz-border-radius: 12px 12px 0 0;">
                                        <!--<![endif]-->
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <!--[if mso]>
                                                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" 
                                                        href="{pub.get('url_pdf', '#')}" 
                                                        style="height:40px;v-text-anchor:middle;width:180px;" 
                                                        arcsize="15%" 
                                                        stroke="f" 
                                                        fillcolor="#6b7280">
                                                        <w:anchorlock/>
                                                        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:500;">Ver documento oficial</center>
                                                    </v:roundrect>
                                                    <![endif]-->
                                                    <!--[if !mso]><!-->
                                                    <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                                                        <tr>
                                                            <td align="left">
                                                                <a href="{pub.get('url_pdf', '#')}" 
                                                                   style="background-color: #6b7280; 
                                                                          border: 1px solid #6b7280;
                                                                          border-radius: 6px; 
                                                                          color: #ffffff; 
                                                                          display: inline-block; 
                                                                          font-family: Arial, sans-serif;
                                                                          font-size: 14px; 
                                                                          font-weight: 500; 
                                                                          line-height: 1;
                                                                          padding: 12px 24px;
                                                                          text-align: center;
                                                                          text-decoration: none; 
                                                                          -webkit-border-radius: 6px; 
                                                                          -moz-border-radius: 6px;
                                                                          mso-hide: all;">
                                                                    Ver documento oficial
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    <!--<![endif]-->
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # Sección Normas Particulares
    if normas_particulares:
        html += """
                            <!-- NORMAS PARTICULARES (DIARIO OFICIAL) -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eff6ff;">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 2px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        NORMAS PARTICULARES
                                                    </h2>
                                                    <p style="margin: 0; font-size: 14px; color: #6b7280;">
                                                        Resoluciones y decretos de alcance específico
                                                    </p>
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        for pub in normas_particulares[:3]:  # Top 3
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <!--[if mso]>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 3px 0 0 0; background-color: #94a3b8;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff;">
                                                        <tr>
                                                            <td class="section-padding" style="padding: 24px;">
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td class="section-padding" style="padding: 24px; border-top: 3px solid #94a3b8; border-radius: 12px 12px 0 0; -webkit-border-radius: 12px 12px 0 0; -moz-border-radius: 12px 12px 0 0;">
                                        <!--<![endif]-->
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <!--[if mso]>
                                                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" 
                                                        href="{pub.get('url_pdf', '#')}" 
                                                        style="height:40px;v-text-anchor:middle;width:180px;" 
                                                        arcsize="15%" 
                                                        stroke="f" 
                                                        fillcolor="#94a3b8">
                                                        <w:anchorlock/>
                                                        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:500;">Ver documento oficial</center>
                                                    </v:roundrect>
                                                    <![endif]-->
                                                    <!--[if !mso]><!-->
                                                    <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                                                        <tr>
                                                            <td align="left">
                                                                <a href="{pub.get('url_pdf', '#')}" 
                                                                   style="background-color: #94a3b8; 
                                                                          border: 1px solid #94a3b8;
                                                                          border-radius: 6px; 
                                                                          color: #ffffff; 
                                                                          display: inline-block; 
                                                                          font-family: Arial, sans-serif;
                                                                          font-size: 14px; 
                                                                          font-weight: 500; 
                                                                          line-height: 1;
                                                                          padding: 12px 24px;
                                                                          text-align: center;
                                                                          text-decoration: none; 
                                                                          -webkit-border-radius: 6px; 
                                                                          -moz-border-radius: 6px;
                                                                          mso-hide: all;">
                                                                    Ver documento oficial
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    <!--<![endif]-->
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # Sección Avisos Destacados
    if avisos_destacados:
        html += """
                            <!-- AVISOS DESTACADOS (DIARIO OFICIAL) -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eff6ff;">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 2px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        AVISOS DESTACADOS
                                                    </h2>
                                                    <p style="margin: 0; font-size: 14px; color: #6b7280;">
                                                        Avisos importantes y notificaciones
                                                    </p>
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        for pub in avisos_destacados[:3]:  # Top 3
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <!--[if mso]>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 3px 0 0 0; background-color: #64748b;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff;">
                                                        <tr>
                                                            <td class="section-padding" style="padding: 24px;">
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td class="section-padding" style="padding: 24px; border-top: 3px solid #64748b; border-radius: 12px 12px 0 0; -webkit-border-radius: 12px 12px 0 0; -moz-border-radius: 12px 12px 0 0;">
                                        <!--<![endif]-->
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <!--[if mso]>
                                                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" 
                                                        href="{pub.get('url_pdf', '#')}" 
                                                        style="height:40px;v-text-anchor:middle;width:180px;" 
                                                        arcsize="15%" 
                                                        stroke="f" 
                                                        fillcolor="#64748b">
                                                        <w:anchorlock/>
                                                        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:500;">Ver documento oficial</center>
                                                    </v:roundrect>
                                                    <![endif]-->
                                                    <!--[if !mso]><!-->
                                                    <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                                                        <tr>
                                                            <td align="left">
                                                                <a href="{pub.get('url_pdf', '#')}" 
                                                                   style="background-color: #64748b; 
                                                                          border: 1px solid #64748b;
                                                                          border-radius: 6px; 
                                                                          color: #ffffff; 
                                                                          display: inline-block; 
                                                                          font-family: Arial, sans-serif;
                                                                          font-size: 14px; 
                                                                          font-weight: 500; 
                                                                          line-height: 1;
                                                                          padding: 12px 24px;
                                                                          text-align: center;
                                                                          text-decoration: none; 
                                                                          -webkit-border-radius: 6px; 
                                                                          -moz-border-radius: 6px;
                                                                          mso-hide: all;">
                                                                    Ver documento oficial
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    <!--<![endif]-->
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # Sección SII (siempre mostrar)
    if True:  # Siempre mostrar la sección
        html += """
                            <!-- PUBLICACIONES SII -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eff6ff;">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 2px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        SERVICIO DE IMPUESTOS INTERNOS
                                                    </h2>
                                                    <p style="margin: 0; font-size: 14px; color: #2563eb;">
                                                        Resoluciones, circulares y oficios
                                                    </p>
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        if not publicaciones_sii:
            # Mensaje cuando no hay publicaciones
            html += """
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px;">
                                            <tr>
                                                <td class="section-padding" style="padding: 24px; text-align: center;">
                                                    <p style="margin: 0; font-size: 14px; color: #64748b; font-style: italic;">
                                                        No se encontraron circulares, resoluciones ni jurisprudencia nueva
                                                    </p>
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        else:
            for pub in publicaciones_sii[:5]:  # Top 5
                # Validar URL
                url_documento = pub.get('url', '')
                if not url_documento or url_documento == '#':
                    url_documento = 'https://www.sii.cl/normativa_legislacion/'
                
                # Formatear tipo y número
                tipo_doc = pub.get('tipo', 'Documento')
                numero_doc = pub.get('numero', 'S/N')
                titulo_completo = f"{tipo_doc} N° {numero_doc}"
                
                # Fecha
                fecha_pub = pub.get('fecha_publicacion', '')
                if not fecha_pub:
                    fecha_pub = fecha  # Usar fecha del informe como fallback
                
                html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <!--[if mso]>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 3px 0 0 0; background-color: #2563eb;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff;">
                                                        <tr>
                                                            <td class="section-padding" style="padding: 24px;">
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td class="section-padding" style="padding: 24px; border-top: 3px solid #2563eb; border-radius: 12px 12px 0 0; -webkit-border-radius: 12px 12px 0 0; -moz-border-radius: 12px 12px 0 0;">
                                        <!--<![endif]-->
                                                    <h3 style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {titulo_completo}
                                                    </h3>
                                                    <div style="margin: 0 0 12px 0; font-size: 13px; color: #6b7280;">
                                                        <span style="font-weight: 500;">Fecha:</span> {fecha_pub}
                                                    </div>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('titulo', 'Sin descripción disponible')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <!--[if mso]>
                                                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" 
                                                        href="{url_documento}" 
                                                        style="height:40px;v-text-anchor:middle;width:160px;" 
                                                        arcsize="15%" 
                                                        stroke="f" 
                                                        fillcolor="#2563eb">
                                                        <w:anchorlock/>
                                                        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:500;">Ver documento SII</center>
                                                    </v:roundrect>
                                                    <![endif]-->
                                                    <!--[if !mso]><!-->
                                                    <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                                                        <tr>
                                                            <td align="left">
                                                                <a href="{url_documento}" 
                                                                   style="background-color: #2563eb; 
                                                                          border: 1px solid #2563eb;
                                                                          border-radius: 6px; 
                                                                          color: #ffffff; 
                                                                          display: inline-block; 
                                                                          font-family: Arial, sans-serif;
                                                                          font-size: 14px; 
                                                                          font-weight: 500; 
                                                                          line-height: 1;
                                                                          padding: 12px 24px;
                                                                          text-align: center;
                                                                          text-decoration: none; 
                                                                          -webkit-border-radius: 6px; 
                                                                          -moz-border-radius: 6px;
                                                                          mso-hide: all;">
                                                                    Ver documento SII
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    <!--<![endif]-->
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # Sección CMF
    if hechos_cmf:
        html += """
                            <!-- HECHOS ESENCIALES CMF -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eff6ff;">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 2px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        HECHOS ESENCIALES - CMF
                                                    </h2>
                                                    <p style="margin: 0; font-size: 14px; color: #7c3aed;">
                                                        Información relevante del mercado de valores
                                                    </p>
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        for hecho in hechos_cmf:
            # Usar el enlace directo si está disponible
            url_hecho = hecho.get('url_pdf', 'https://www.cmfchile.cl/institucional/hechos/hechos.php')
            
            # Obtener categoría (sin icono ni badge)
            
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <!--[if mso]>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 3px 0 0 0; background-color: #7c3aed;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff;">
                                                        <tr>
                                                            <td class="section-padding" style="padding: 24px;">
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td class="section-padding" style="padding: 24px; border-top: 3px solid #7c3aed; border-radius: 12px 12px 0 0; -webkit-border-radius: 12px 12px 0 0; -moz-border-radius: 12px 12px 0 0;">
                                        <!--<![endif]-->
                                                    <h3 style="margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        {hecho.get('entidad', '')}
                                                    </h3>
                                                    <div style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #6b7280;">
                                                        {hecho.get('titulo', hecho.get('materia', ''))}
                                                    </div>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {hecho.get('resumen', '')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <!--[if mso]>
                                                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" 
                                                        href="{url_hecho}" 
                                                        style="height:40px;v-text-anchor:middle;width:180px;" 
                                                        arcsize="15%" 
                                                        stroke="f" 
                                                        fillcolor="#7c3aed">
                                                        <w:anchorlock/>
                                                        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:500;">Ver hecho esencial</center>
                                                    </v:roundrect>
                                                    <![endif]-->
                                                    <!--[if !mso]><!-->
                                                    <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                                                        <tr>
                                                            <td align="left">
                                                                <a href="{url_hecho}" 
                                                                   style="background-color: #7c3aed; 
                                                                          border: 1px solid #7c3aed;
                                                                          border-radius: 6px; 
                                                                          color: #ffffff; 
                                                                          display: inline-block; 
                                                                          font-family: Arial, sans-serif;
                                                                          font-size: 14px; 
                                                                          font-weight: 500; 
                                                                          line-height: 1;
                                                                          padding: 12px 24px;
                                                                          text-align: center;
                                                                          text-decoration: none; 
                                                                          -webkit-border-radius: 6px; 
                                                                          -moz-border-radius: 6px;
                                                                          mso-hide: all;">
                                                                    Ver hecho esencial
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    <!--<![endif]-->
                                                <!--[if mso]>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        <![endif]-->
                                        <!--[if !mso]><!-->
                                                </td>
                                            </tr>
                                        <!--<![endif]-->
                                        </table>
                                    </td>
                                </tr>"""
        
        html += """
                            </table>"""
    
    # Valores de monedas
    if valores_monedas:
        html += f"""
                            <!-- VALORES DE MONEDAS -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eff6ff;">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 2px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        Valores del Día
                                                    </h2>
                                                    <p style="margin: 0; font-size: 14px; color: #2563eb;">
                                                        Tipos de cambio oficiales
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td class="mobile-block" width="50%" style="padding: 16px; background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; text-align: center;">
                                                    <div style="font-size: 14px; color: #0369a1; margin-bottom: 4px;">Dólar Observado</div>
                                                    <div style="font-size: 24px; font-weight: 700; color: #0c4a6e;">${valores_monedas.get('dolar', 'N/A')}</div>
                                                </td>
                                                <td class="mobile-block" width="8"></td>
                                                <td class="mobile-block" width="50%" style="padding: 16px; background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; text-align: center;">
                                                    <div style="font-size: 14px; color: #0369a1; margin-bottom: 4px;">Euro</div>
                                                    <div style="font-size: 24px; font-weight: 700; color: #0c4a6e;">€{valores_monedas.get('euro', 'N/A')}</div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>"""
    
    # Footer
    html += """
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td class="content-padding" style="background-color: #f8fafc; padding: 24px 32px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p class="small-text" style="margin: 0; font-size: 13px; color: #64748b; line-height: 1.5;">
                                Información obtenida directamente de fuentes oficiales
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
            </td>
        </tr>
    </table>
    
</body>
</html>"""
    
    return html

def enviar_informe_email(html, fecha):
    """
    Envía el informe por email a TODOS los destinatarios
    """
    # Importar modelo de destinatarios
    from alerts.models import Destinatario
    
    # Configuración desde variables de entorno
    de_email = 'contacto@informediariochile.cl'  # Siempre usar este email
    password = os.getenv('HOSTINGER_EMAIL_PASSWORD', '')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.hostinger.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    # Verificar si es un informe de bienvenida (solo para casos especiales)
    es_bienvenida = os.getenv('INFORME_ES_BIENVENIDA', 'false') == 'true'
    
    if es_bienvenida:
        # Caso especial: envío de bienvenida a un solo destinatario
        para_email = os.getenv('INFORME_DESTINATARIO_TEMP', 'rfernandezdelrio@uc.cl')
        destinatarios = [para_email]
        logger.info("Modo bienvenida: enviando a un solo destinatario")
    else:
        # Caso normal: obtener TODOS los destinatarios de la base de datos
        destinatarios = list(Destinatario.objects.values_list('email', flat=True))
        if not destinatarios:
            logger.warning("No hay destinatarios registrados en la base de datos")
            return
        logger.info(f"Enviando a {len(destinatarios)} destinatarios registrados")
    
    # Verificar que tenemos la contraseña
    if not password:
        logger.error("❌ Error: No se encontró la contraseña del email")
        logger.error("   Asegúrate de tener el archivo .env con HOSTINGER_EMAIL_PASSWORD")
        return
    
    # Formatear fecha para el asunto
    fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
    fecha_formato = formatear_fecha_espanol(fecha_obj)
    
    logger.info(f"📧 Preparando envío a {len(destinatarios)} destinatarios...")
    
    # Conectar al servidor SMTP una sola vez
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(de_email, password)
        
        enviados = 0
        errores = 0
        
        # Enviar a cada destinatario
        for email_destinatario in destinatarios:
            # Crear mensaje individual para cada destinatario
            msg = MIMEMultipart('alternative')
            msg['From'] = de_email
            msg['To'] = email_destinatario
            
            # Ajustar asunto según si es bienvenida o no
            if es_bienvenida:
                msg['Subject'] = f"Bienvenido a Informe Diario - Ejemplo del {fecha_formato}"
            else:
                msg['Subject'] = f"Informe Diario • {fecha_formato}"
            
            # Agregar contenido HTML
            html_part = MIMEText(html, 'html', 'utf-8')
            msg.attach(html_part)
            
            try:
                # Enviar mensaje individual
                server.send_message(msg)
                enviados += 1
                logger.info(f"✅ Enviado a: {email_destinatario}")
            except Exception as e:
                errores += 1
                logger.error(f"❌ Error enviando a {email_destinatario}: {str(e)}")
        
        server.quit()
        
        logger.info(f"\n📊 RESUMEN DE ENVÍO:")
        logger.info(f"   ✅ Enviados exitosamente: {enviados}")
        logger.info(f"   ❌ Errores: {errores}")
        logger.info(f"   📧 Total destinatarios: {len(destinatarios)}")
        
    except Exception as e:
        logger.error(f"Error crítico al conectar con servidor SMTP: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        fecha = sys.argv[1]  # Formato: DD-MM-YYYY
        generar_informe_oficial(fecha)
    else:
        generar_informe_oficial()