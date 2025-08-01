#!/usr/bin/env python
"""
Script de prueba sin input interactivo para generar el informe del Diario Oficial
"""
import os
import sys
import django
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.scraper_diario_oficial import obtener_sumario_diario_oficial
from django.template import engines

def main():
    """Prueba el sistema con la fecha del 21 de julio"""
    
    fecha = "21-07-2025"
    
    print(f"=== PROBANDO GENERACIÓN DE INFORME DEL {fecha} ===\n")
    
    # Verificar que tenemos la API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        print("✅ API key de OpenAI configurada")
        print(f"   Primeros caracteres: {api_key[:20]}...")
    else:
        print("❌ No se encontró API key de OpenAI")
    
    # Ejecutar el scraper
    print("\n1. Ejecutando scraper del Diario Oficial...")
    print(f"   Fecha: {fecha}")
    
    try:
        resultado = obtener_sumario_diario_oficial(fecha)
        
        if not resultado:
            print("❌ Error: No se obtuvieron resultados del scraper")
            return
        
        publicaciones = resultado.get('publicaciones', [])
        valores_monedas = resultado.get('valores_monedas', {})
        total_documentos = resultado.get('total_documentos', 0)
        
        print(f"\n✅ Resultados del scraper:")
        print(f"   - Total documentos analizados: {total_documentos}")
        print(f"   - Publicaciones relevantes: {len(publicaciones)}")
        if valores_monedas:
            print(f"   - Valores de monedas encontrados: {', '.join(valores_monedas.keys())}")
        
        # Mostrar algunas publicaciones con resúmenes
        if publicaciones:
            print("\n📄 Primeras 3 publicaciones con resúmenes:")
            for i, pub in enumerate(publicaciones[:3], 1):
                print(f"\n   {i}. {pub.get('titulo', 'Sin título')}")
                if pub.get('resumen'):
                    print(f"      ✅ Resumen generado con IA:")
                    print(f"      {pub['resumen'][:200]}...")
                else:
                    print(f"      ❌ Sin resumen (posible problema con API)")
        
        # Generar HTML
        print("\n2. Generando HTML con la plantilla oficial...")
        
        # Organizar publicaciones por sección
        secciones_dict = {}
        
        for pub in publicaciones:
            titulo = pub.get('titulo', '')
            if "decreto" in titulo.lower():
                seccion = "DECRETOS"
            elif "resolución" in titulo.lower():
                seccion = "RESOLUCIONES"
            elif "ley" in titulo.lower():
                seccion = "LEYES"
            else:
                seccion = pub.get('seccion', 'NORMAS GENERALES')
            
            if seccion not in secciones_dict:
                secciones_dict[seccion] = {
                    'nombre': seccion,
                    'descripcion': f'Documentos oficiales de tipo {seccion.lower()}',
                    'publicaciones': []
                }
            
            pub_completa = {
                'titulo': pub.get('titulo', ''),
                'url_pdf': pub.get('url_pdf', ''),
                'resumen': pub.get('resumen', ''),
                'relevante': pub.get('relevante', True),
                'es_licitacion': pub.get('es_licitacion', False)
            }
            
            secciones_dict[seccion]['publicaciones'].append(pub_completa)
        
        # Convertir a lista ordenada
        secciones = list(secciones_dict.values())
        orden_prioridad = ['LEYES', 'DECRETOS', 'RESOLUCIONES', 'NORMAS GENERALES']
        secciones.sort(key=lambda x: orden_prioridad.index(x['nombre']) if x['nombre'] in orden_prioridad else 999)
        
        # Leer la plantilla
        with open('templates/informe_diario_oficial_plantilla.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Usar Django template engine
        django_engine = engines['django']
        template = django_engine.from_string(template_content)
        
        # Obtener número de edición
        edicion_numero = "44.203"
        if os.path.exists('edition_cache.json'):
            import json
            with open('edition_cache.json', 'r') as f:
                cache = json.load(f)
                if fecha in cache:
                    numero = int(cache[fecha])
                    edicion_numero = f"{numero:,}".replace(",", ".")
        
        context = {
            'fecha': fecha,
            'fecha_formato': '21 de Julio, 2025',
            'edicion_numero': edicion_numero,
            'total_documentos': total_documentos,
            'publicaciones_relevantes': len(publicaciones),
            'secciones': secciones,
            'valores_monedas': valores_monedas
        }
        
        html = template.render(context)
        
        # Guardar copia
        filename = f"informe_test_api_{fecha.replace('-', '_')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"📄 Informe guardado en: {filename}")
        
        print("\n✅ Prueba completada")
        print(f"   - Publicaciones procesadas: {len(publicaciones)}")
        print(f"   - Secciones generadas: {len(secciones)}")
        
        # Verificar calidad de resúmenes
        con_resumen = sum(1 for p in publicaciones if p.get('resumen'))
        print(f"\n📊 Calidad de procesamiento:")
        print(f"   - Publicaciones con resumen IA: {con_resumen}/{len(publicaciones)}")
        if con_resumen < len(publicaciones):
            print(f"   ⚠️  Algunas publicaciones no tienen resumen (verificar API)")
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()