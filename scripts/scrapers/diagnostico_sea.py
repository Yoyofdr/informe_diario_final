#!/usr/bin/env python3
"""
Diagnóstico del sitio SEA para entender qué datos están disponibles
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

def diagnosticar_sea():
    """Diagnóstica qué datos están disponibles en el SEA"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Language': 'es-ES,es;q=0.9'
    })
    
    print("\n" + "=" * 80)
    print("🔍 DIAGNÓSTICO COMPLETO DEL SITIO SEA/SEIA")
    print("=" * 80)
    
    # 1. Probar endpoint de búsqueda principal
    print("\n1️⃣ PROBANDO ENDPOINT DE BÚSQUEDA PRINCIPAL")
    print("-" * 40)
    
    url = "https://seia.sea.gob.cl/busqueda/buscarProyectoAction.php"
    
    fecha_hasta = datetime.now()
    fecha_desde = fecha_hasta - timedelta(days=7)
    
    params = {
        '_': str(int(datetime.now().timestamp() * 1000))
    }
    
    try:
        response = session.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"Tamaño respuesta: {len(response.text)} caracteres")
        
        # Intentar parsear como JSON
        try:
            data = response.json()
            print(f"✅ Respuesta es JSON")
            print(f"Tipo de datos: {type(data)}")
            
            if isinstance(data, list):
                print(f"Número de elementos: {len(data)}")
                if data:
                    print("\nPrimer elemento:")
                    print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
            elif isinstance(data, dict):
                print("Claves del diccionario:")
                for key in data.keys():
                    print(f"  - {key}")
                    
        except json.JSONDecodeError:
            print("❌ Respuesta NO es JSON, es HTML")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar tablas
            tablas = soup.find_all('table')
            print(f"Tablas encontradas: {len(tablas)}")
            
            # Buscar formularios
            forms = soup.find_all('form')
            print(f"Formularios encontrados: {len(forms)}")
            
            # Primeras 500 caracteres del HTML
            print("\nPrimeros 500 caracteres del HTML:")
            print(response.text[:500])
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 2. Probar página de búsqueda
    print("\n2️⃣ PROBANDO PÁGINA DE BÚSQUEDA DIRECTA")
    print("-" * 40)
    
    url_busqueda = "https://seia.sea.gob.cl/busqueda/buscarProyecto.php"
    
    try:
        response = session.get(url_busqueda, timeout=10)
        print(f"Status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar campos de formulario
        inputs = soup.find_all('input')
        print(f"\nCampos de entrada encontrados: {len(inputs)}")
        
        for inp in inputs[:10]:
            name = inp.get('name', 'sin-nombre')
            tipo = inp.get('type', 'text')
            value = inp.get('value', '')
            if name != 'sin-nombre':
                print(f"  - {name} (tipo: {tipo})")
        
        # Buscar selects
        selects = soup.find_all('select')
        print(f"\nSelectores encontrados: {len(selects)}")
        for sel in selects:
            name = sel.get('name', 'sin-nombre')
            if name != 'sin-nombre':
                print(f"  - {name}")
                options = sel.find_all('option')[:5]
                for opt in options:
                    print(f"    • {opt.text.strip()}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 3. Buscar proyectos del 26 de agosto específicamente
    print("\n3️⃣ BUSCANDO PROYECTOS DEL 26/08/2025")
    print("-" * 40)
    
    # Intentar con fecha específica
    params_26 = {
        'fecha_desde': '26/08/2025',
        'fecha_hasta': '26/08/2025',
        '_': str(int(datetime.now().timestamp() * 1000))
    }
    
    try:
        response = session.get(
            "https://seia.sea.gob.cl/busqueda/buscarProyectoAction.php",
            params=params_26,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        try:
            data = response.json()
            if isinstance(data, list):
                print(f"✅ Proyectos encontrados para 26/08: {len(data)}")
                
                # Mostrar todos los proyectos encontrados
                for i, proyecto in enumerate(data, 1):
                    print(f"\n{i}. Proyecto encontrado:")
                    for key, value in proyecto.items():
                        if value and str(value).strip():
                            print(f"   {key}: {value}")
                            
        except json.JSONDecodeError:
            print("Respuesta HTML, parseando...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar cualquier texto que contenga "agosto" o "26"
            textos = soup.find_all(text=lambda text: '26' in text or 'agosto' in text.lower())
            print(f"Referencias a fecha encontradas: {len(textos)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 4. Probar página principal
    print("\n4️⃣ ANALIZANDO PÁGINA PRINCIPAL")
    print("-" * 40)
    
    try:
        response = session.get("https://seia.sea.gob.cl/", timeout=10)
        print(f"Status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar enlaces a proyectos
        enlaces = soup.find_all('a', href=lambda x: x and ('expediente' in x or 'proyecto' in x))
        print(f"Enlaces a proyectos: {len(enlaces)}")
        
        if enlaces:
            print("\nPrimeros 5 enlaces:")
            for enlace in enlaces[:5]:
                texto = enlace.text.strip()[:60]
                href = enlace.get('href', '')
                if texto:
                    print(f"  - {texto}")
                    print(f"    URL: {href}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("📊 FIN DEL DIAGNÓSTICO")
    print("=" * 80)


if __name__ == "__main__":
    diagnosticar_sea()