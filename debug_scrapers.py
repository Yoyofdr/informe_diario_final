#!/usr/bin/env python
"""
Debug de scrapers ambientales - Ver datos crudos de APIs
"""

import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup

print("\n" + "="*70)
print("🔍 DEBUG DE SCRAPERS AMBIENTALES - DATOS CRUDOS")
print("="*70)

# 1. Probar endpoint AJAX del SEIA
print("\n📊 1. Probando endpoint AJAX del SEIA...")
try:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    })
    
    # Primero obtener cookies
    session.get("https://seia.sea.gob.cl/busqueda/buscarProyectoResumen.php")
    
    # Luego hacer petición AJAX
    response = session.get(
        "https://seia.sea.gob.cl/busqueda/buscarProyectoResumenAction.php",
        params={
            'draw': '1',
            'start': '0',
            'length': '10',
            'order[0][column]': '13',
            'order[0][dir]': 'desc'
        },
        timeout=15
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"   ✅ Respuesta JSON recibida")
            print(f"   - Total registros: {data.get('recordsTotal', 0)}")
            print(f"   - Registros en respuesta: {len(data.get('data', []))}")
            
            if 'data' in data and data['data']:
                print("\n   Primeros 3 proyectos:")
                for i, item in enumerate(data['data'][:3], 1):
                    print(f"\n   {i}. Proyecto:")
                    print(f"      - Nombre: {item.get('EXPEDIENTE_NOMBRE', 'Sin nombre')}")
                    print(f"      - Empresa: {item.get('TITULAR', 'Sin titular')}")
                    print(f"      - Fecha timestamp: {item.get('FECHA_PRESENTACION', 'Sin fecha')}")
                    print(f"      - Fecha formateada: {item.get('FECHA_PRESENTACION_FORMAT', 'Sin formato')}")
                    print(f"      - Estado: {item.get('ESTADO_PROYECTO', 'Sin estado')}")
                    print(f"      - Región: {item.get('REGION_NOMBRE', 'Sin región')}")
                    
                    # Convertir timestamp si existe
                    timestamp = item.get('FECHA_PRESENTACION')
                    if timestamp and str(timestamp).isdigit():
                        fecha = datetime.fromtimestamp(int(timestamp))
                        print(f"      - Fecha convertida: {fecha.strftime('%d/%m/%Y')}")
            else:
                print("   ⚠️ No hay datos en la respuesta")
                
        except json.JSONDecodeError as e:
            print(f"   ❌ Error parseando JSON: {e}")
            print(f"   Respuesta cruda: {response.text[:500]}")
    else:
        print(f"   ❌ Error HTTP: {response.status_code}")
        
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# 2. Probar endpoint del SNIFA
print("\n📊 2. Probando endpoint del SNIFA (Registro Público)...")
try:
    response = requests.get(
        "https://snifa.sma.gob.cl/RegistroPublico/Resultado/2025",
        timeout=30
    )
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar tabla
        tabla = soup.find('table')
        if tabla:
            filas = tabla.find_all('tr')
            print(f"   ✅ Tabla encontrada con {len(filas)} filas")
            
            # Analizar headers
            if filas:
                headers = filas[0].find_all(['th', 'td'])
                print(f"\n   Headers de la tabla ({len(headers)} columnas):")
                for i, header in enumerate(headers):
                    print(f"      {i}: {header.get_text(strip=True)}")
                
                # Ver primera fila de datos
                if len(filas) > 1:
                    print(f"\n   Primera fila de datos:")
                    celdas = filas[1].find_all(['td', 'th'])
                    for i, celda in enumerate(celdas):
                        texto = celda.get_text(strip=True)[:50]
                        print(f"      Columna {i}: {texto}")
        else:
            print("   ⚠️ No se encontró tabla en la página")
            
            # Buscar si hay datos en otro formato
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'data' in script.string.lower():
                    print("   📌 Encontrado script con posibles datos")
                    break
    else:
        print(f"   ❌ Error HTTP: {response.status_code}")
        
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# 3. Buscar alternativas para datos actuales
print("\n📊 3. Buscando endpoints alternativos...")

# Probar API v2 del SNIFA
print("\n   Probando API v2 del SNIFA...")
try:
    response = requests.get(
        "https://snifa.sma.gob.cl/v2/Sancionatorios",
        timeout=30
    )
    print(f"   - v2/Sancionatorios: Status {response.status_code}")
    
    if response.status_code == 200:
        # Ver si es JSON o HTML
        try:
            data = response.json()
            print(f"     ✅ Respuesta JSON con {len(data)} items" if isinstance(data, list) else f"     ✅ Respuesta JSON (dict)")
        except:
            print(f"     📄 Respuesta HTML ({len(response.text)} caracteres)")
            
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print("\n" + "="*70)
print("ANÁLISIS")
print("="*70)
print("""
Los scrapers actuales tienen estos problemas:
1. El endpoint AJAX del SEIA puede estar devolviendo datos antiguos o con cache
2. Las tablas del SNIFA no incluyen fechas en las columnas principales
3. Necesitamos buscar endpoints alternativos o parsear más profundo

Soluciones propuestas:
1. Para SEA: Filtrar por fecha y buscar endpoints de proyectos recientes
2. Para SMA: Extraer fecha del número de expediente o buscar en detalles
3. Implementar validación de fechas para excluir datos muy antiguos
""")