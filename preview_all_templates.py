#!/usr/bin/env python3
import os
import webbrowser
from pathlib import Path

# Rutas a las plantillas originales
templates = {
    "Landing Explicativa": "informe_diario_final_repo/templates/alerts/landing_explicativa.html",
    "Dashboard": "informe_diario_final_repo/templates/alerts/dashboard.html", 
    "Login": "informe_diario_final_repo/templates/registration/login.html",
    "Registro": "informe_diario_final_repo/templates/alerts/registro_prueba.html",
    "Base (con navbar)": "informe_diario_final_repo/templates/alerts/base.html"
}

print("🖼️  PREVIEW DE PLANTILLAS ORIGINALES")
print("=" * 50)
print("\nAbriendo las siguientes plantillas en tu navegador:\n")

for name, path in templates.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        file_url = f"file://{full_path.absolute()}"
        print(f"✓ {name}: {path}")
        webbrowser.open(file_url)
    else:
        print(f"✗ {name}: No encontrado en {path}")

print("\n📝 Nota: Las plantillas se abrirán en pestañas separadas de tu navegador.")
print("    El dashboard necesita Django para funcionar correctamente (extiende base.html)")