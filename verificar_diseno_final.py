#!/usr/bin/env python3
"""
Script para verificar que el diseño del informe está correcto
después de eliminar los comentarios MSO
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
import django
django.setup()

from scripts.generators.generar_informe_oficial_integrado_mejorado import generar_html_informe
from datetime import datetime

def verificar_diseno():
    print("=" * 60)
    print("VERIFICACIÓN DE DISEÑO POST-MSO")
    print("=" * 60)
    
    # Datos de prueba
    fecha = "13-08-2025"
    
    resultado_diario = {
        'publicaciones': [
            {
                'titulo': 'Decreto N° 123 - Ministerio de Hacienda',
                'resumen': 'Modifica reglamento sobre operaciones de cambio internacionales.',
                'url_pdf': 'https://ejemplo.com/decreto123.pdf',
                'seccion': 'NORMAS GENERALES'
            },
            {
                'titulo': 'Resolución Exenta N° 456',
                'resumen': 'Aprueba bases de licitación pública.',
                'url_pdf': 'https://ejemplo.com/res456.pdf',
                'seccion': 'NORMAS PARTICULARES'
            }
        ],
        'valores_monedas': {
            'dolar': '945.32',
            'euro': '1,025.45'
        }
    }
    
    hechos_cmf = [
        {
            'entidad': 'BANCO SANTANDER CHILE',
            'titulo': 'Cambio en la administración',
            'resumen': 'Se informa el nombramiento de nuevo director independiente.',
            'url_pdf': 'https://cmf.cl/hecho123.pdf'
        }
    ]
    
    publicaciones_sii = [
        {
            'tipo': 'Circular',
            'numero': '45',
            'titulo': 'Nuevas instrucciones sobre facturación electrónica',
            'fecha_publicacion': '12 de agosto, 2025',
            'url': 'https://sii.cl/circular45.pdf'
        }
    ]
    
    # Generar HTML
    print("\n📝 Generando HTML del informe...")
    html = generar_html_informe(fecha, resultado_diario, hechos_cmf, publicaciones_sii)
    
    # Guardar archivo para inspección
    archivo_prueba = "verificacion_diseno_final.html"
    with open(archivo_prueba, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML generado y guardado en: {archivo_prueba}")
    
    # Verificaciones críticas
    print("\n🔍 VERIFICACIONES CRÍTICAS:")
    print("-" * 40)
    
    # 1. No debe haber comentarios MSO
    tiene_mso = "<!--[if mso]>" in html
    print(f"1. Sin comentarios MSO: {'❌ FALLO' if tiene_mso else '✅ OK'}")
    
    # 2. Verificar elementos clave del diseño
    elementos_criticos = [
        ("Header oscuro", 'background-color: #0f172a'),
        ("Título principal", 'Informe Diario'),
        ("Botón gris", 'background-color: #6b7280'),
        ("Botón azul CMF", 'background-color: #7c3aed'),
        ("Botón azul SII", 'background-color: #2563eb'),
        ("Border radius", 'border-radius: 6px'),
        ("Padding botones", 'padding: 12px 24px'),
        ("Tabla principal", 'max-width: 672px'),
        ("Secciones", 'NORMAS GENERALES'),
        ("Valores monedas", 'Dólar Observado')
    ]
    
    for nombre, elemento in elementos_criticos:
        existe = elemento in html
        print(f"2. {nombre}: {'✅ OK' if existe else '❌ FALLO'}")
    
    # 3. Verificar estructura de botones
    print("\n📊 ANÁLISIS DE BOTONES:")
    print("-" * 40)
    
    # Contar botones
    num_botones = html.count('Ver documento')
    print(f"Total de botones encontrados: {num_botones}")
    
    # Verificar que los botones tienen la estructura correcta
    boton_correcto = '<table cellpadding="0" cellspacing="0" border="0" role="presentation">' in html
    print(f"Estructura de tabla para botones: {'✅ OK' if boton_correcto else '❌ FALLO'}")
    
    # 4. Tamaño del HTML
    tamano_kb = len(html) / 1024
    print(f"\n📏 TAMAÑO DEL HTML: {tamano_kb:.2f} KB")
    if tamano_kb < 50:
        print("   ✅ Tamaño óptimo (< 50KB)")
    elif tamano_kb < 100:
        print("   ⚠️ Tamaño aceptable (< 100KB)")
    else:
        print("   ❌ Tamaño excesivo (> 100KB)")
    
    # Resumen final
    print("\n" + "=" * 60)
    if not tiene_mso and boton_correcto and tamano_kb < 100:
        print("✅ VERIFICACIÓN EXITOSA")
        print("El diseño está correcto y listo para producción")
    else:
        print("❌ HAY PROBLEMAS QUE REVISAR")
    print("=" * 60)
    
    return archivo_prueba

if __name__ == "__main__":
    archivo = verificar_diseno()
    print(f"\n💡 Puedes abrir {archivo} en un navegador para ver el diseño visual")