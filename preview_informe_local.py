#!/usr/bin/env python
"""
Script para previsualizar el informe en un navegador local
Simula tanto la vista de Gmail como la de Outlook
"""
import os
import sys
from datetime import datetime
import pytz
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import threading

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
import django
django.setup()

# Importar después de configurar Django
from alerts.models import InformeDiarioCache

class InformeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Página principal con opciones
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Preview Informe Diario</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 40px 20px;
                        background: #f5f5f5;
                    }
                    h1 {
                        color: #333;
                        text-align: center;
                        margin-bottom: 40px;
                    }
                    .container {
                        background: white;
                        border-radius: 12px;
                        padding: 40px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }
                    .button-group {
                        display: flex;
                        gap: 20px;
                        justify-content: center;
                        margin-top: 30px;
                    }
                    .btn {
                        display: inline-block;
                        padding: 15px 30px;
                        font-size: 16px;
                        font-weight: 600;
                        text-decoration: none;
                        border-radius: 8px;
                        transition: all 0.3s;
                        text-align: center;
                        min-width: 200px;
                    }
                    .btn-gmail {
                        background: #4285f4;
                        color: white;
                    }
                    .btn-gmail:hover {
                        background: #357ae8;
                    }
                    .btn-outlook {
                        background: #0078d4;
                        color: white;
                    }
                    .btn-outlook:hover {
                        background: #106ebe;
                    }
                    .btn-raw {
                        background: #6c757d;
                        color: white;
                    }
                    .btn-raw:hover {
                        background: #5a6268;
                    }
                    .info {
                        background: #f8f9fa;
                        border-left: 4px solid #0078d4;
                        padding: 20px;
                        margin: 30px 0;
                        border-radius: 4px;
                    }
                    .info h3 {
                        margin-top: 0;
                        color: #0078d4;
                    }
                    .info ul {
                        margin: 10px 0;
                        padding-left: 20px;
                    }
                    .info li {
                        margin: 5px 0;
                    }
                </style>
            </head>
            <body>
                <h1>🔍 Preview del Informe Diario</h1>
                <div class="container">
                    <h2>Selecciona cómo quieres ver el informe:</h2>
                    
                    <div class="info">
                        <h3>📧 Modos de visualización disponibles:</h3>
                        <ul>
                            <li><strong>Vista Gmail:</strong> Muestra el informe como se vería en Gmail, Apple Mail y otros clientes modernos (con border-radius y estilos CSS3)</li>
                            <li><strong>Vista Outlook:</strong> Simula cómo se ve en Microsoft Outlook (solo estilos básicos, sin border-radius)</li>
                            <li><strong>HTML Raw:</strong> Muestra el código HTML completo con ambas versiones</li>
                        </ul>
                    </div>
                    
                    <div class="button-group">
                        <a href="/gmail" class="btn btn-gmail">📬 Ver como Gmail</a>
                        <a href="/outlook" class="btn btn-outlook">📮 Ver como Outlook</a>
                        <a href="/raw" class="btn btn-raw">📄 Ver HTML Raw</a>
                    </div>
                    
                    <div class="info" style="margin-top: 40px;">
                        <h3>💡 Diferencias principales:</h3>
                        <ul>
                            <li><strong>Bordes:</strong> Gmail muestra bordes redondeados, Outlook muestra bordes rectos</li>
                            <li><strong>Botones:</strong> Gmail muestra botones estilizados, Outlook muestra tablas con color de fondo</li>
                            <li><strong>Espaciado:</strong> Puede variar ligeramente entre clientes</li>
                            <li><strong>Colores:</strong> Se mantienen consistentes en ambos</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif self.path in ['/gmail', '/outlook', '/raw']:
            # Obtener el informe más reciente de la caché
            chile_tz = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(chile_tz).strftime("%Y-%m-%d")
            
            try:
                cache = InformeDiarioCache.objects.filter(fecha=fecha_hoy).first()
                if cache:
                    contenido_html = cache.contenido_html
                else:
                    # Si no hay caché de hoy, generar uno nuevo
                    import importlib.util
                    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py')
                    spec = importlib.util.spec_from_file_location("generar_informe", script_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    fecha = datetime.now(chile_tz).strftime("%d-%m-%Y")
                    module.generar_informe_oficial(fecha)
                    
                    # Intentar obtener de nuevo
                    cache = InformeDiarioCache.objects.filter(fecha=fecha_hoy).first()
                    contenido_html = cache.contenido_html if cache else "<h1>No se pudo generar el informe</h1>"
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                if self.path == '/gmail':
                    # Eliminar código MSO para simular Gmail
                    import re
                    # Eliminar bloques MSO
                    contenido_limpio = re.sub(r'<!--\[if mso\]>.*?<!\[endif\]-->', '', contenido_html, flags=re.DOTALL)
                    # Mantener contenido no-MSO
                    contenido_limpio = re.sub(r'<!--\[if !mso\]><!-->|<!--<!\[endif\]-->', '', contenido_limpio)
                    
                    html_wrapper = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>Vista Gmail - Informe Diario</title>
                        <style>
                            body {{
                                margin: 0;
                                padding: 20px;
                                background: #f5f5f5;
                            }}
                            .email-container {{
                                max-width: 672px;
                                margin: 0 auto;
                                background: white;
                                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                            }}
                            .header-bar {{
                                background: #f8f9fa;
                                padding: 15px;
                                border-bottom: 1px solid #e0e0e0;
                                font-family: Arial, sans-serif;
                                font-size: 14px;
                                color: #666;
                            }}
                            .header-bar strong {{
                                color: #333;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="email-container">
                            <div class="header-bar">
                                <strong>Vista Gmail</strong> - Así se ve el informe en Gmail, Apple Mail y otros clientes modernos
                                <a href="/" style="float: right; color: #4285f4; text-decoration: none;">← Volver</a>
                            </div>
                            {contenido_limpio}
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(html_wrapper.encode())
                    
                elif self.path == '/outlook':
                    # Eliminar código no-MSO para simular Outlook
                    import re
                    # Mantener solo bloques MSO
                    contenido_outlook = contenido_html
                    # Eliminar comentarios condicionales
                    contenido_outlook = re.sub(r'<!--\[if mso\]>|<!\[endif\]-->', '', contenido_outlook)
                    # Eliminar bloques no-MSO
                    contenido_outlook = re.sub(r'<!--\[if !mso\]><!-->.*?<!--<!\[endif\]-->', '', contenido_outlook, flags=re.DOTALL)
                    # Eliminar border-radius y otras propiedades no soportadas
                    contenido_outlook = re.sub(r'border-radius:\s*[^;]+;?', '', contenido_outlook)
                    contenido_outlook = re.sub(r'-webkit-border-radius:\s*[^;]+;?', '', contenido_outlook)
                    contenido_outlook = re.sub(r'-moz-border-radius:\s*[^;]+;?', '', contenido_outlook)
                    contenido_outlook = re.sub(r'box-shadow:\s*[^;]+;?', '', contenido_outlook)
                    
                    html_wrapper = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>Vista Outlook - Informe Diario</title>
                        <style>
                            body {{
                                margin: 0;
                                padding: 20px;
                                background: #f5f5f5;
                            }}
                            .email-container {{
                                max-width: 672px;
                                margin: 0 auto;
                                background: white;
                                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                            }}
                            .header-bar {{
                                background: #0078d4;
                                color: white;
                                padding: 15px;
                                font-family: Arial, sans-serif;
                                font-size: 14px;
                            }}
                            .header-bar a {{
                                color: white;
                                text-decoration: none;
                                float: right;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="email-container">
                            <div class="header-bar">
                                <strong>Vista Outlook</strong> - Así se ve el informe en Microsoft Outlook
                                <a href="/">← Volver</a>
                            </div>
                            {contenido_outlook}
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(html_wrapper.encode())
                    
                elif self.path == '/raw':
                    # Mostrar HTML completo
                    html_wrapper = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>HTML Raw - Informe Diario</title>
                        <style>
                            body {{
                                margin: 0;
                                padding: 20px;
                                background: #f5f5f5;
                                font-family: monospace;
                            }}
                            .container {{
                                max-width: 1200px;
                                margin: 0 auto;
                                background: white;
                                padding: 20px;
                                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                            }}
                            .header-bar {{
                                background: #6c757d;
                                color: white;
                                padding: 15px;
                                margin: -20px -20px 20px -20px;
                                font-family: Arial, sans-serif;
                            }}
                            .header-bar a {{
                                color: white;
                                text-decoration: none;
                                float: right;
                            }}
                            pre {{
                                white-space: pre-wrap;
                                word-wrap: break-word;
                                background: #f8f9fa;
                                padding: 15px;
                                border: 1px solid #dee2e6;
                                border-radius: 4px;
                                overflow-x: auto;
                            }}
                            .rendered {{
                                border: 2px solid #dee2e6;
                                padding: 20px;
                                margin: 20px 0;
                                background: white;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header-bar">
                                <strong>HTML Raw</strong> - Código HTML completo con ambas versiones (MSO y no-MSO)
                                <a href="/">← Volver</a>
                            </div>
                            <h2>Vista renderizada:</h2>
                            <div class="rendered">
                                {contenido_html}
                            </div>
                            <h2>Código HTML:</h2>
                            <pre>{contenido_html.replace('<', '&lt;').replace('>', '&gt;')}</pre>
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(html_wrapper.encode())
                    
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                error_html = f"""
                <html>
                <body>
                    <h1>Error al cargar el informe</h1>
                    <p>{str(e)}</p>
                    <p><a href="/">Volver</a></p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suprimir logs del servidor
        pass

def start_server():
    port = 8888
    server = HTTPServer(('localhost', port), InformeHandler)
    print(f"\n📧 Servidor de preview iniciado en: http://localhost:{port}")
    print("   Presiona Ctrl+C para detener el servidor\n")
    
    # Abrir navegador automáticamente
    def open_browser():
        webbrowser.open(f'http://localhost:{port}')
    
    threading.Timer(1, open_browser).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")
        server.shutdown()

if __name__ == '__main__':
    start_server()