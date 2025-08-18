#!/usr/bin/env python3
"""
Preview del correo de bienvenida en localhost
"""
import http.server
import socketserver
import webbrowser
from datetime import datetime

# HTML del correo de bienvenida
html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bienvenido a Informe Diario</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; padding: 50px 20px;">
        <tr>
            <td align="center">
                
                <!-- Container -->
                <table width="500" cellpadding="0" cellspacing="0" style="max-width: 500px; width: 100%; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 35px 40px; background-color: #0f172a; text-align: center;">
                            <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.025em;">
                                INFORME DIARIO
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            
                            <p style="margin: 0 0 20px 0; font-size: 17px; color: #1e293b; line-height: 1.6;">
                                Hola Juan Pérez,
                            </p>
                            
                            <p style="margin: 0 0 25px 0; font-size: 16px; color: #475569; line-height: 1.6;">
                                Tu cuenta ha sido creada exitosamente.
                            </p>
                            
                            <p style="margin: 0 0 30px 0; font-size: 16px; color: #475569; line-height: 1.6;">
                                <strong style="color: #1e293b;">Email:</strong> juan.perez@ejemplo.com
                            </p>
                            
                            <p style="margin: 0 0 30px 0; font-size: 16px; color: #475569; line-height: 1.6;">
                                Ya puedes iniciar sesión en la plataforma.
                            </p>
                            
                            <p style="margin: 0; font-size: 17px; color: #1e293b; line-height: 1.6;">
                                ¡Bienvenido!
                            </p>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; background-color: #f8fafc; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-size: 13px; color: #64748b;">
                                © 2025 Informe Diario • Santiago, Chile
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
            </td>
        </tr>
    </table>
    
</body>
</html>
"""

# Crear servidor HTTP
class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode())

PORT = 8002
print(f"🚀 Servidor iniciado en http://localhost:{PORT}")
print("📧 Mostrando preview del correo de bienvenida")
print("   Presiona Ctrl+C para detener el servidor")

# Abrir navegador automáticamente
webbrowser.open(f'http://localhost:{PORT}')

# Iniciar servidor
with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    httpd.serve_forever()