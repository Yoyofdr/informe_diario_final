#!/usr/bin/env python3
import webbrowser
import time

print("🌐 ABRIENDO PREVIEWS DE LOS TEMPLATES ACTUALES")
print("=" * 50)
print("\nEl servidor Django está corriendo en http://localhost:8001")
print("\nAbriendo las siguientes páginas:\n")

urls = {
    "Landing Explicativa (Principal)": "http://localhost:8001/",
    "Login": "http://localhost:8001/login/",
    "Registro": "http://localhost:8001/registro-prueba/",
    "Dashboard (requiere login)": "http://localhost:8001/dashboard/",
}

for name, url in urls.items():
    print(f"✓ {name}: {url}")
    webbrowser.open(url)
    time.sleep(0.5)

print("\n📝 Nota: El Dashboard requiere estar logueado para verlo.")
print("    Estos son los templates de Chennai que están actualmente en el proyecto.")