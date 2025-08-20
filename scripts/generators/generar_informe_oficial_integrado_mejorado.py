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
import time
from collections import defaultdict
from email import utils as email_utils

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
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Permitir modo oscuro pero con colores específicos preservados -->
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
    <meta name="x-apple-disable-message-reformatting">
    <title>Informe Diario • {fecha}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style>
        /* Permitir modo oscuro con colores específicos preservados */
        :root {{
            color-scheme: light dark;
            supported-color-schemes: light dark;
        }}
        
        /* Reset global para modo oscuro */
        * {{
            -webkit-text-size-adjust: none !important;
            -ms-text-size-adjust: none !important;
        }}
        
        /* Prevenir inversión de colores en Gmail y otros clientes */
        u + .body .wrapper {{
            background-color: #ffffff !important;
        }}
        
        /* Adaptación inteligente para modo oscuro */
        @media (prefers-color-scheme: dark) {{
            /* Fondos oscuros para mejor legibilidad */
            body {{
                background-color: #1a1a1a !important;
                color: #e5e5e5 !important;
            }}
            
            .wrapper {{
                background-color: #242424 !important;
            }}
            
            table {{
                background-color: #242424 !important;
            }}
            
            td {{
                color: #e5e5e5 !important;
            }}
            
            h1, h2, h3, h4, h5, h6 {{
                color: #ffffff !important;
            }}
            
            p, div, span, li {{
                color: #e5e5e5 !important;
            }}
            
            a {{
                color: #60a5fa !important;
            }}
            
            /* PRESERVAR: Banner principal siempre negro */
            .dark-header,
            .dark-header td,
            .header-table,
            [style*="background-color: #0f172a"] {{
                background-color: #0f172a !important;
                background-image: none !important;
            }}
            
            .dark-header h1,
            .dark-header p {{
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }}
            
            /* PRESERVAR: Colores morados de CMF */
            .badge-cmf,
            .cmf-card,
            [style*="border-top: 3px solid #8b5cf6"],
            [style*="background-color: #8b5cf6"],
            [style*="background: linear-gradient(135deg, #8b5cf6"],
            td[style*="#8b5cf6"] {{
                border-top-color: #8b5cf6 !important;
            }}
            
            /* Preservar color morado en subtítulos */
            .cmf-subtitle,
            [style*="color: #8b5cf6"] {{
                color: #8b5cf6 !important;
                -webkit-text-fill-color: #8b5cf6 !important;
            }}
            
            /* Para elementos con fondo morado */
            .badge-cmf,
            [style*="background-color: #8b5cf6"] {{
                background-color: #8b5cf6 !important;
                background-image: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }}
            
            /* PRESERVAR: Otros colores de badges */
            .badge-sii,
            [style*="background-color: #ef4444"],
            td[style*="#ef4444"] {{
                background-color: #ef4444 !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }}
            
            .badge-diario,
            [style*="background-color: #3b82f6"],
            td[style*="#3b82f6"] {{
                background-color: #3b82f6 !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }}
            
            /* Adaptar tarjetas de contenido para modo oscuro */
            .content-card {{
                background-color: #2a2a2a !important;
                border-color: #404040 !important;
            }}
            
            /* Bordes más visibles en modo oscuro */
            table[style*="border"],
            td[style*="border"] {{
                border-color: #404040 !important;
            }}
            
            [style*="color: #64748b"] {{
                color: #64748b !important;
                -webkit-text-fill-color: #64748b !important;
            }}
            
            [style*="color: #6b7280"] {{
                color: #6b7280 !important;
                -webkit-text-fill-color: #6b7280 !important;
            }}
            
            [style*="background-color: #ffffff"] {{
                background-color: #ffffff !important;
            }}
            
            [style*="background-color: #f8fafc"] {{
                background-color: #f8fafc !important;
            }}
        }}
        
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
<body class="body" style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc !important; color: #1e293b !important; line-height: 1.6; -webkit-font-smoothing: antialiased; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                
                <!-- Wrapper -->
                <table class="wrapper" width="672" cellpadding="0" cellspacing="0" style="max-width: 672px; width: 100%; background-color: #ffffff !important; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td class="header-padding dark-header" style="background-color: #0f172a !important; padding: 48px 32px; text-align: center;">
                            <h1 style="margin: 0 0 8px 0; font-size: 28px; font-weight: 700; color: #ffffff !important; letter-spacing: -0.025em;">
                                Informe Diario
                            </h1>
                            <p style="margin: 0; font-size: 14px; font-weight: 500; color: #ffffff !important;">
                                {fecha_formato}
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
                                                    <h2 style="margin: 0 0 2px 0; font-size: 18px; font-weight: 600; color: #1e293b !important;">
                                                        NORMAS GENERALES
                                                    </h2>
                                                    <p style="margin: 0; font-size: 14px; color: #6b7280 !important;">
                                                        Leyes, decretos supremos y resoluciones de alcance general
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>"""
        
        for pub in normas_generales[:3]:  # Top 3
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff !important; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 20px; border-top: 3px solid #6b7280; background-color: #ffffff !important;">
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b !important; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b !important; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td>
                                                                <table border="0" cellspacing="0" cellpadding="0">
                                                                    <tr>
                                                                        <td align="center" style="border-radius: 6px; background-color: #6b7280 !important;" bgcolor="#6b7280">
                                                                            <a href="{pub.get('url_pdf', '#')}" target="_blank" style="font-size: 14px; font-family: Arial, sans-serif; color: #ffffff !important; text-decoration: none; border-radius: 6px; padding: 12px 24px; border: 1px solid #6b7280; display: inline-block; font-weight: 500; background-color: #6b7280 !important;">
                                                                                Ver documento oficial
                                                                            </a>
                                                                        </td>
                                                                    </tr>
                                                                </table>
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
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>"""
        
        for pub in normas_particulares[:3]:  # Top 3
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td style="padding: 24px; border-top: 3px solid #94a3b8;">
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td>
                                                                <table border="0" cellspacing="0" cellpadding="0">
                                                                    <tr>
                                                                        <td align="center" style="border-radius: 6px;" bgcolor="#94a3b8">
                                                                            <a href="{pub.get('url_pdf', '#')}" target="_blank" style="font-size: 14px; font-family: Arial, sans-serif; color: #ffffff; text-decoration: none; border-radius: 6px; padding: 12px 24px; border: 1px solid #94a3b8; display: inline-block; font-weight: 500;">
                                                                                Ver documento oficial
                                                                            </a>
                                                                        </td>
                                                                    </tr>
                                                                </table>
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
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>"""
        
        for pub in avisos_destacados[:3]:  # Top 3
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0;">
                                            <tr>
                                                <td style="padding: 20px; border-top: 3px solid #64748b;">
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <!-- Botón compatible con Outlook -->
                                                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td>
                                                                <table border="0" cellspacing="0" cellpadding="0">
                                                                    <tr>
                                                                        <td align="center" style="border-radius: 6px;" bgcolor="#64748b">
                                                                            <a href="{pub.get('url_pdf', '#')}" target="_blank" style="font-size: 14px; font-family: Arial, sans-serif; color: #ffffff; text-decoration: none; border-radius: 6px; padding: 12px 24px; border: 1px solid #64748b; display: inline-block; font-weight: 500;">
                                                                                Ver documento oficial
                                                                            </a>
                                                                        </td>
                                                                    </tr>
                                                                </table>
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
                                                </td>
                                            </tr>
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
                                                        No se encontraron circulares, resoluciones ni jurisprudencia relevante
                                                    </p>
                                                </td>
                                            </tr>
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
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td class="section-padding" style="padding: 24px; border-top: 3px solid #2563eb; border-radius: 12px 12px 0 0; -webkit-border-radius: 12px 12px 0 0; -moz-border-radius: 12px 12px 0 0;">
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
                                                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td>
                                                                <table border="0" cellspacing="0" cellpadding="0">
                                                                    <tr>
                                                                        <td align="center" style="border-radius: 6px;" bgcolor="#2563eb">
                                                                            <a href="{url_documento}" target="_blank" style="font-size: 14px; font-family: Arial, sans-serif; color: #ffffff; text-decoration: none; border-radius: 6px; padding: 12px 24px; border: 1px solid #2563eb; display: inline-block; font-weight: 500;">
                                                                                Ver documento SII
                                                                            </a>
                                                                        </td>
                                                                    </tr>
                                                                </table>
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
                                                    <p class="cmf-subtitle" style="margin: 0; font-size: 14px; color: #8b5cf6;">
                                                        Información relevante del mercado de valores
                                                    </p>
                                                </td>
                                            </tr>
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
                                        <table width="100%" cellpadding="0" cellspacing="0" class="content-card" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; -webkit-border-radius: 12px; -moz-border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td class="section-padding cmf-card" style="padding: 24px; border-top: 3px solid #8b5cf6; border-radius: 12px 12px 0 0; -webkit-border-radius: 12px 12px 0 0; -moz-border-radius: 12px 12px 0 0;">
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
                                                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td>
                                                                <table border="0" cellspacing="0" cellpadding="0">
                                                                    <tr>
                                                                        <td align="center" style="border-radius: 6px;" bgcolor="#7c3aed">
                                                                            <a href="{url_hecho}" target="_blank" style="font-size: 14px; font-family: Arial, sans-serif; color: #ffffff; text-decoration: none; border-radius: 6px; padding: 12px 24px; border: 1px solid #7c3aed; display: inline-block; font-weight: 500;">
                                                                                Ver hecho esencial
                                                                            </a>
                                                                        </td>
                                                                    </tr>
                                                                </table>
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
    
    # Verificar si hay destinatarios específicos para prueba
    destinatarios_prueba = os.getenv('INFORME_DESTINATARIOS_PRUEBA', '')
    
    if es_bienvenida:
        # Caso especial: envío de bienvenida a un solo destinatario
        para_email = os.getenv('INFORME_DESTINATARIO_TEMP', 'rfernandezdelrio@uc.cl')
        destinatarios = [para_email]
        logger.info("Modo bienvenida: enviando a un solo destinatario")
    elif destinatarios_prueba:
        # Modo prueba: enviar solo a destinatarios específicos
        destinatarios = [email.strip() for email in destinatarios_prueba.split(',')]
        logger.info(f"MODO PRUEBA: enviando solo a {len(destinatarios)} destinatarios específicos: {destinatarios}")
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
    print(f"📧 Preparando envío a {len(destinatarios)} destinatarios...")  # También imprimir para mayor visibilidad
    
    # Mostrar los primeros 5 destinatarios para verificar
    logger.info(f"Primeros destinatarios: {destinatarios[:5]}...")
    print(f"Primeros destinatarios: {destinatarios[:5]}...")
    
    # Conectar al servidor SMTP una sola vez
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(de_email, password)
        
        enviados = 0
        errores = 0
        emails_fallidos = []
        
        # Configuración de throttling para dominios Microsoft
        microsoft_domains = ('@outlook.', '@hotmail.', '@live.', '@msn.', '@outlook.es', '@outlook.cl')
        office365_domains = ('@bye.cl', '@pgb.cl', '@carvuk.com')  # Agregar dominios conocidos de clientes con M365
        
        # Control de ventana de tiempo para throttling
        ventana = defaultdict(lambda: {'count': 0, 'ts': time.time()})
        limite_por_minuto = {
            'microsoft': 20,  # 20 emails por minuto para dominios Microsoft
            'office365': 25,  # 25 emails por minuto para clientes M365
            'otros': 60       # 60 emails por minuto para otros
        }
        
        def get_bucket(email):
            """Determina el bucket del email para throttling"""
            email_lower = email.lower()
            if any(email_lower.endswith(d) for d in microsoft_domains):
                return 'microsoft'
            if any(email_lower.endswith(d) for d in office365_domains):
                return 'office365'
            return 'otros'
        
        # Enviar a cada destinatario con throttling
        for email_destinatario in destinatarios:
            # Determinar bucket y aplicar throttling
            bucket = get_bucket(email_destinatario)
            now = time.time()
            
            # Resetear ventana si pasó 1 minuto
            if now - ventana[bucket]['ts'] >= 60:
                ventana[bucket] = {'count': 0, 'ts': now}
            
            # Si alcanzamos el límite, esperar
            if ventana[bucket]['count'] >= limite_por_minuto.get(bucket, 60):
                sleep_time = 60 - (now - ventana[bucket]['ts'])
                if sleep_time > 0:
                    logger.info(f"⏳ Throttling: esperando {sleep_time:.1f}s para bucket {bucket}")
                    time.sleep(sleep_time)
                ventana[bucket] = {'count': 0, 'ts': time.time()}
            
            # Crear mensaje individual para cada destinatario
            msg = MIMEMultipart('alternative')
            msg['From'] = de_email
            msg['To'] = email_destinatario
            
            # Ajustar asunto según si es bienvenida o no
            if es_bienvenida:
                msg['Subject'] = f"Bienvenido a Informe Diario - Ejemplo del {fecha_formato}"
            else:
                msg['Subject'] = f"Informe Diario • {fecha_formato}"
            
            # IMPORTANTE: Agregar headers recomendados para mejor entregabilidad
            msg['Date'] = email_utils.formatdate(localtime=True)
            msg['Message-ID'] = email_utils.make_msgid(domain="informediariochile.cl")
            msg['MIME-Version'] = '1.0'
            
            # Headers opcionales pero recomendados
            msg['List-Unsubscribe'] = f'<https://informediariochile.cl/unsubscribe?email={email_destinatario}>'
            msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
            msg['X-Mailer'] = 'Informe Diario Chile v1.0'
            msg['X-Priority'] = '3'  # Normal priority
            
            # Agregar contenido HTML
            html_part = MIMEText(html, 'html', 'utf-8')
            msg.attach(html_part)
            
            try:
                # Enviar mensaje individual con envelope-from explícito
                server.send_message(msg, from_addr=de_email, to_addrs=[email_destinatario])
                enviados += 1
                ventana[bucket]['count'] += 1
                logger.info(f"✅ Enviado a: {email_destinatario} [bucket: {bucket}]")
                print(f"✅ Enviado a: {email_destinatario}")  # También imprimir
            except Exception as e:
                errores += 1
                emails_fallidos.append(email_destinatario)
                logger.error(f"❌ Error enviando a {email_destinatario}: {str(e)}")
                print(f"❌ Error enviando a {email_destinatario}: {str(e)}")  # También imprimir
                
                # Si es un error de autenticación o conexión, reconectar
                if "connection" in str(e).lower() or "auth" in str(e).lower():
                    try:
                        logger.info("Reconectando al servidor SMTP...")
                        server.quit()
                        server = smtplib.SMTP(smtp_server, smtp_port)
                        server.starttls()
                        server.login(de_email, password)
                    except:
                        pass
        
        server.quit()
        
        logger.info(f"\n📊 RESUMEN DE ENVÍO:")
        logger.info(f"   ✅ Enviados exitosamente: {enviados}")
        logger.info(f"   ❌ Errores: {errores}")
        logger.info(f"   📧 Total destinatarios: {len(destinatarios)}")
        
        # También imprimir para mayor visibilidad
        print(f"\n📊 RESUMEN DE ENVÍO:")
        print(f"   ✅ Enviados exitosamente: {enviados}")
        print(f"   ❌ Errores: {errores}")
        print(f"   📧 Total destinatarios: {len(destinatarios)}")
        
        if emails_fallidos:
            logger.error(f"\n❌ EMAILS QUE FALLARON:")
            print(f"\n❌ EMAILS QUE FALLARON:")
            for email in emails_fallidos:
                logger.error(f"   - {email}")
                print(f"   - {email}")
        
    except Exception as e:
        logger.error(f"Error crítico al conectar con servidor SMTP: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        fecha = sys.argv[1]  # Formato: DD-MM-YYYY
        generar_informe_oficial(fecha)
    else:
        generar_informe_oficial()