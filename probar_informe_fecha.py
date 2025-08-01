#!/usr/bin/env python
"""
Script de prueba para generar el informe del Diario Oficial de una fecha específica
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
    """Prueba el sistema con una fecha específica o la del usuario"""
    
    # Permitir pasar fecha como argumento
    if len(sys.argv) > 1:
        fecha = sys.argv[1]
    else:
        # Usar fecha conocida con publicaciones (21 de julio)
        fecha = "21-07-2025"
    
    print(f"=== PROBANDO GENERACIÓN DE INFORME DEL {fecha} ===\n")
    
    # Ejecutar el scraper
    print("1. Ejecutando scraper del Diario Oficial...")
    print(f"   Fecha: {fecha}")
    
    try:
        resultado = obtener_sumario_diario_oficial(fecha)
        
        if not resultado:
            print("❌ Error: No se obtuvieron resultados del scraper")
            print("   Nota: Es posible que no haya publicación para esta fecha")
            return
        
        publicaciones = resultado.get('publicaciones', [])
        valores_monedas = resultado.get('valores_monedas', {})
        total_documentos = resultado.get('total_documentos', 0)
        
        print(f"\n✅ Resultados del scraper:")
        print(f"   - Total documentos analizados: {total_documentos}")
        print(f"   - Publicaciones relevantes: {len(publicaciones)}")
        if valores_monedas:
            print(f"   - Valores de monedas encontrados: {', '.join(valores_monedas.keys())}")
        
        # Mostrar algunas publicaciones de ejemplo
        if publicaciones:
            print("\n📄 Primeras 5 publicaciones encontradas:")
            for i, pub in enumerate(publicaciones[:5], 1):
                print(f"\n   {i}. {pub.get('titulo', 'Sin título')}")
                print(f"      URL: {pub.get('url_pdf', 'No disponible')}")
                if pub.get('resumen'):
                    print(f"      Resumen: {pub['resumen'][:150]}...")
        
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
        
        # Mostrar resumen de secciones
        print("\n📊 Distribución por secciones:")
        for seccion in secciones:
            print(f"   - {seccion['nombre']}: {len(seccion['publicaciones'])} publicaciones")
        
        # Generar HTML con la plantilla oficial
        print("\n2. Generando HTML con la plantilla oficial...")
        
        # Verificar que existe la plantilla
        if not os.path.exists('templates/informe_diario_oficial_plantilla.html'):
            print("❌ Error: No se encuentra la plantilla oficial")
            return
        
        # Leer la plantilla
        with open('templates/informe_diario_oficial_plantilla.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Usar Django template engine
        django_engine = engines['django']
        template = django_engine.from_string(template_content)
        
        # Formatear fecha para mostrar
        try:
            fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
            meses = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }
            fecha_formato = f"{fecha_obj.day} de {meses[fecha_obj.month]}, {fecha_obj.year}"
        except:
            fecha_formato = fecha
        
        # Obtener número de edición del cache si está disponible
        edicion_numero = "Sin información"
        if os.path.exists('edition_cache.json'):
            import json
            with open('edition_cache.json', 'r') as f:
                cache = json.load(f)
                if fecha in cache:
                    # Formatear número con separador de miles
                    numero = int(cache[fecha])
                    edicion_numero = f"{numero:,}".replace(",", ".")
        
        context = {
            'fecha': fecha,
            'fecha_formato': fecha_formato,
            'edicion_numero': edicion_numero,
            'total_documentos': total_documentos,
            'publicaciones_relevantes': len(publicaciones),
            'secciones': secciones,
            'valores_monedas': valores_monedas
        }
        
        html = template.render(context)
        
        # Guardar copia
        filename = f"informe_prueba_{fecha.replace('-', '_')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"📄 Informe guardado en: {filename}")
        
        print("\n✅ Prueba completada exitosamente")
        print(f"   - Publicaciones procesadas: {len(publicaciones)}")
        print(f"   - Secciones generadas: {len(secciones)}")
        print(f"   - Archivo HTML creado: {filename}")
        
        # Preguntar si quiere enviar por email
        if publicaciones:
            print("\n¿Deseas enviar este informe por email? (s/n): ", end='', flush=True)
            respuesta = input().strip().lower()
            
            if respuesta == 's':
                print("\nEnviando email...")
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"Informe Diario Oficial - {fecha_formato} (Edición {edicion_numero})"
                msg['From'] = "rodrigo@carvuk.com"
                msg['To'] = "rfernandezdelrio@uc.cl"
                
                html_part = MIMEText(html, 'html')
                msg.attach(html_part)
                
                try:
                    server = smtplib.SMTP("smtp.gmail.com", 587)
                    server.starttls()
                    server.login("rodrigo@carvuk.com", "swqjlcwjaoooyzcb")
                    server.send_message(msg)
                    server.quit()
                    
                    print("\n✅ Informe enviado exitosamente")
                    print(f"   De: rodrigo@carvuk.com")
                    print(f"   Para: rfernandezdelrio@uc.cl")
                except Exception as e:
                    print(f"\n❌ Error enviando email: {str(e)}")
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()