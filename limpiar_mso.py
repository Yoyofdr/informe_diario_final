#!/usr/bin/env python3
"""
Script para eliminar todos los comentarios MSO del generador principal
manteniendo el diseño exactamente igual
"""

import re

def limpiar_archivo():
    # Leer el archivo
    with open('scripts/generators/generar_informe_oficial_integrado_mejorado.py', 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Contar comentarios MSO antes
    count_antes = contenido.count('<!--[if mso]>')
    print(f"Comentarios MSO encontrados: {count_antes}")
    
    # Patrón para encontrar bloques MSO completos
    # Busca desde <!--[if mso]> hasta <!--<![endif]-->
    patron = r'<!--\[if mso\]>.*?<!--<!\[endif\]-->'
    
    # Función para reemplazar cada bloque
    def reemplazar_bloque(match):
        bloque = match.group(0)
        # Extraer solo la parte del else (después de <!--[if !mso]><!-->)
        if '<!--[if !mso]><!-->' in bloque:
            # Encontrar el contenido después de <!--[if !mso]><!-->
            partes = bloque.split('<!--[if !mso]><!-->')
            if len(partes) > 1:
                contenido_else = partes[1]
                # Quitar el cierre <!--<![endif]-->
                contenido_else = contenido_else.replace('<!--<![endif]-->', '')
                return contenido_else.strip()
        return ''
    
    # Reemplazar todos los bloques MSO
    contenido_limpio = re.sub(patron, reemplazar_bloque, contenido, flags=re.DOTALL)
    
    # Verificar que no quedan comentarios MSO
    count_despues = contenido_limpio.count('<!--[if mso]>')
    print(f"Comentarios MSO después de limpiar: {count_despues}")
    
    # Guardar el archivo limpio
    with open('scripts/generators/generar_informe_oficial_integrado_mejorado_limpio.py', 'w', encoding='utf-8') as f:
        f.write(contenido_limpio)
    
    print("✅ Archivo limpio guardado como: generar_informe_oficial_integrado_mejorado_limpio.py")
    
    # Sobrescribir el original
    respuesta = input("\n¿Deseas sobrescribir el archivo original? (s/n): ")
    if respuesta.lower() == 's':
        with open('scripts/generators/generar_informe_oficial_integrado_mejorado.py', 'w', encoding='utf-8') as f:
            f.write(contenido_limpio)
        print("✅ Archivo original actualizado")
    else:
        print("ℹ️ El archivo original no fue modificado")

if __name__ == "__main__":
    limpiar_archivo()