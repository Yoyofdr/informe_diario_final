#!/usr/bin/env python3
"""
Script para arreglar los botones en Outlook
Usa una técnica que funciona sin comentarios condicionales MSO
"""

def crear_boton_outlook(texto, url, color_bg):
    """
    Crea un botón que funciona en Outlook y otros clientes
    Sin usar comentarios condicionales MSO
    """
    
    # Para Outlook, necesitamos usar una tabla con celdas con background
    # Esta técnica funciona en todos los clientes sin necesidad de comentarios condicionales
    
    boton_html = f'''
                                                    <!-- Botón universal -->
                                                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td>
                                                                <table border="0" cellspacing="0" cellpadding="0">
                                                                    <tr>
                                                                        <td align="center" style="border-radius: 6px;" bgcolor="{color_bg}">
                                                                            <a href="{url}" target="_blank" style="font-size: 14px; font-family: Arial, sans-serif; color: #ffffff; text-decoration: none; border-radius: 6px; padding: 12px 24px; border: 1px solid {color_bg}; display: inline-block; font-weight: 500;">
                                                                                {texto}
                                                                            </a>
                                                                        </td>
                                                                    </tr>
                                                                </table>
                                                            </td>
                                                        </tr>
                                                    </table>'''
    
    return boton_html

# Test con diferentes colores
print("Ejemplo de botón para NORMAS GENERALES (gris):")
print(crear_boton_outlook("Ver documento oficial", "https://ejemplo.com", "#6b7280"))

print("\nEjemplo de botón para CMF (morado):")
print(crear_boton_outlook("Ver hecho esencial", "https://ejemplo.com", "#7c3aed"))

print("\nEjemplo de botón para SII (azul):")
print(crear_boton_outlook("Ver documento SII", "https://ejemplo.com", "#2563eb"))