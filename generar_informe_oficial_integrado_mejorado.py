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

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

# Importar scrapers
from alerts.scraper_diario_oficial import obtener_sumario_diario_oficial
from scraper_cmf_mejorado import ScraperCMFMejorado
from alerts.cmf_criterios_profesionales import filtrar_hechos_profesional, get_icono_categoria
from alerts.scraper_sii import obtener_circulares_sii, obtener_resoluciones_exentas_sii, obtener_jurisprudencia_administrativa_sii
from alerts.cmf_resumenes_ai import generar_resumen_cmf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                fecha_buscada_str = fecha_anterior.strftime("%d de %B de %Y").replace("January", "Enero").replace("February", "Febrero").replace("March", "Marzo").replace("April", "Abril").replace("May", "Mayo").replace("June", "Junio").replace("July", "Julio").replace("August", "Agosto").replace("September", "Septiembre").replace("October", "Octubre").replace("November", "Noviembre").replace("December", "Diciembre")
                
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
        with open('hechos_cmf_selenium_reales.json', 'r', encoding='utf-8') as f:
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
        fecha = datetime.now().strftime("%d-%m-%Y")
    
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
    fecha_formato = fecha_obj.strftime("%d de %B, %Y").replace("July", "Julio")
    
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
    <title>Informe Diario • {fecha}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc; color: #1e293b; line-height: 1.6;">
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                
                <!-- Wrapper -->
                <table width="672" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 48px 32px; text-align: center;">
                            <h1 style="margin: 0 0 8px 0; font-size: 28px; font-weight: 700; color: #ffffff; letter-spacing: -0.025em;">
                                Informe Diario
                            </h1>
                            <p style="margin: 0; color: #cbd5e1; font-size: 14px; font-weight: 500;">
                                {fecha_formato}
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 32px;">"""
    
    # Agregar mensaje de bienvenida si aplica
    es_bienvenida = os.getenv('INFORME_ES_BIENVENIDA', 'false') == 'true'
    if es_bienvenida:
        nombre_destinatario = os.getenv('INFORME_NOMBRE_TEMP', '')
        html += f"""
                            <!-- MENSAJE DE BIENVENIDA -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 40px;">
                                <tr>
                                    <td style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 24px;">
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
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>"""
        
        for pub in normas_generales[:3]:  # Top 3
            html += f"""
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 24px; border-top: 3px solid #6b7280; border-radius: 12px 12px 0 0;">
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #6b7280; border-radius: 6px;">
                                                                <a href="{pub.get('url_pdf', '#')}" style="display: inline-block; padding: 10px 20px; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 500;">
                                                                    Ver documento oficial
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
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 24px; border-top: 3px solid #94a3b8; border-radius: 12px 12px 0 0;">
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #94a3b8; border-radius: 6px;">
                                                                <a href="{pub.get('url_pdf', '#')}" style="display: inline-block; padding: 10px 20px; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 500;">
                                                                    Ver documento oficial
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
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 24px; border-top: 3px solid #64748b; border-radius: 12px 12px 0 0;">
                                                    <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {pub.get('titulo', '')}
                                                    </h3>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('resumen', '')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #64748b; border-radius: 6px;">
                                                                <a href="{pub.get('url_pdf', '#')}" style="display: inline-block; padding: 10px 20px; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 500;">
                                                                    Ver documento oficial
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
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 24px; text-align: center;">
                                                    <p style="margin: 0; font-size: 14px; color: #64748b; font-style: italic;">
                                                        No se encontraron circulares, resoluciones ni jurisprudencia nueva
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
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 24px; border-top: 3px solid #2563eb; border-radius: 12px 12px 0 0;">
                                                    <h3 style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600; color: #1e293b; line-height: 1.4;">
                                                        {titulo_completo}
                                                    </h3>
                                                    <div style="margin: 0 0 12px 0; font-size: 13px; color: #6b7280;">
                                                        <span style="font-weight: 500;">Fecha:</span> {fecha_pub}
                                                    </div>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {pub.get('titulo', 'Sin descripción disponible')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #2563eb; border-radius: 6px;">
                                                                <a href="{url_documento}" style="display: inline-block; padding: 10px 20px; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 500;">
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
                                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 24px; border-top: 3px solid #7c3aed; border-radius: 12px 12px 0 0;">
                                                    <h3 style="margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: #1e293b;">
                                                        {hecho.get('entidad', '')}
                                                    </h3>
                                                    <div style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #6b7280;">
                                                        {hecho.get('titulo', hecho.get('materia', ''))}
                                                    </div>
                                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #64748b; line-height: 1.6;">
                                                        {hecho.get('resumen', '')}
                                                    </p>
                                                    <table cellpadding="0" cellspacing="0">
                                                        <tr>
                                                            <td style="background-color: #7c3aed; border-radius: 6px;">
                                                                <a href="{url_hecho}" style="display: inline-block; padding: 10px 20px; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 500;">
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
                                                <td width="50%" style="padding: 16px; background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; text-align: center;">
                                                    <div style="font-size: 14px; color: #0369a1; margin-bottom: 4px;">Dólar Observado</div>
                                                    <div style="font-size: 24px; font-weight: 700; color: #0c4a6e;">${valores_monedas.get('dolar', 'N/A')}</div>
                                                </td>
                                                <td width="8"></td>
                                                <td width="50%" style="padding: 16px; background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; text-align: center;">
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
                        <td style="background-color: #f8fafc; padding: 24px 32px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-size: 13px; color: #64748b; line-height: 1.5;">
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
    Envía el informe por email
    """
    # Configuración desde variables de entorno
    de_email = os.getenv('EMAIL_FROM', 'contacto@informediariochile.cl')
    
    # Verificar si es un informe de bienvenida
    es_bienvenida = os.getenv('INFORME_ES_BIENVENIDA', 'false') == 'true'
    
    if es_bienvenida:
        # Usar destinatario temporal para bienvenida
        para_email = os.getenv('INFORME_DESTINATARIO_TEMP', 'rfernandezdelrio@uc.cl')
        nombre_destinatario = os.getenv('INFORME_NOMBRE_TEMP', '')
    else:
        # Usar destinatario por defecto
        para_email = os.getenv('DEFAULT_TO_EMAIL', 'rfernandezdelrio@uc.cl')
        nombre_destinatario = ''
    
    password = os.getenv('HOSTINGER_EMAIL_PASSWORD', '')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.hostinger.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    # Verificar que tenemos la contraseña
    if not password:
        logger.error("❌ Error: No se encontró la contraseña del email")
        logger.error("   Asegúrate de tener el archivo .env con HOSTINGER_EMAIL_PASSWORD")
        return
    
    # Formatear fecha para el asunto
    fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
    fecha_formato = fecha_obj.strftime("%d de %B, %Y").replace("July", "Julio")
    
    # Crear mensaje
    msg = MIMEMultipart('alternative')
    msg['From'] = de_email
    msg['To'] = para_email
    
    # Ajustar asunto según si es bienvenida o no
    if es_bienvenida:
        msg['Subject'] = f"Bienvenido a Informe Diario - Ejemplo del {fecha_formato}"
    else:
        msg['Subject'] = f"Informe Diario • {fecha_formato}"
    
    # Agregar contenido HTML
    html_part = MIMEText(html, 'html', 'utf-8')
    msg.attach(html_part)
    
    try:
        # Enviar
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(de_email, password)
        server.send_message(msg)
        server.quit()
        
        logger.info("✅ Informe enviado exitosamente!")
        logger.info(f"   De: {de_email}")
        logger.info(f"   Para: {para_email}")
        
    except Exception as e:
        logger.error(f"Error al enviar email: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        fecha = sys.argv[1]  # Formato: DD-MM-YYYY
        generar_informe_oficial(fecha)
    else:
        generar_informe_oficial()