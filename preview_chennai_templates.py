#!/usr/bin/env python3
import webbrowser
from pathlib import Path

# Templates de Chennai que estaban en Heroku esta mañana
templates = {
    "Chennai - Landing Explicativa": "preview_chennai_landing.html",
    "Chennai - Dashboard": "preview_chennai_dashboard.html",
    "Chennai - Login": "preview_chennai_login.html",
    "Chennai - Registro": "preview_chennai_registro.html"
}

print("🖼️  PREVIEW DE TEMPLATES CHENNAI (Heroku esta mañana)")
print("=" * 50)
print("\nAbriendo los templates que estaban en producción:\n")

for name, filename in templates.items():
    full_path = Path(__file__).parent / filename
    if full_path.exists():
        file_url = f"file://{full_path.absolute()}"
        print(f"✓ {name}")
        webbrowser.open(file_url)
    else:
        print(f"✗ {name}: No encontrado")

print("\n📝 Estos son los templates de Chennai que estaban funcionando esta mañana en Heroku.")
print("    Todos tienen font Inter y diseño moderno sin navbar (excepto dashboard).")