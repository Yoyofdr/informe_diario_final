#!/usr/bin/env python
"""
Script para verificar el estado de las API keys
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("=== VERIFICACIÓN DE API KEYS ===\n")

# 1. API Key local
print("1. API KEY LOCAL (.env):")
api_key_local = os.environ.get('OPENAI_API_KEY', '')
if api_key_local:
    print(f"   Encontrada: {api_key_local[:20]}...{api_key_local[-4:]}")
    print(f"   Longitud: {len(api_key_local)} caracteres")
    
    # Verificar formato
    if api_key_local.startswith('sk-'):
        print("   Formato: ✅ Parece válida")
    else:
        print("   Formato: ❌ No parece válida")
        
    # La API key que está fallando
    if "tR4A" in api_key_local:
        print("   ⚠️  Esta es la API key que está fallando")
else:
    print("   ❌ No encontrada")

# 2. Otras API keys en el entorno
print("\n2. OTRAS API KEYS ENCONTRADAS:")
otras_keys = {
    'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY'),
    'DEEPSEEK_API_KEY': os.environ.get('DEEPSEEK_API_KEY'),
    'HF_API_TOKEN': os.environ.get('HF_API_TOKEN')
}

for nombre, valor in otras_keys.items():
    if valor:
        print(f"   {nombre}: {valor[:10]}...")
    else:
        print(f"   {nombre}: No configurada")

# 3. Verificar archivo .env
print("\n3. CONTENIDO DEL ARCHIVO .env:")
try:
    with open('.env', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if 'OPENAI_API_KEY' in line and not line.strip().startswith('#'):
                print(f"   {line.strip()[:50]}...")
except Exception as e:
    print(f"   Error leyendo .env: {e}")

# 4. Recomendaciones
print("\n4. SITUACIÓN:")
print("=" * 50)
print("La API key local está expirada o es inválida.")
print("En Heroku probablemente tengas una API key diferente y válida.")
print("\nOPCIONES:")
print("1. Actualizar la API key local en el archivo .env")
print("2. Usar una API key alternativa (Gemini, DeepSeek)")
print("3. Verificar la configuración en Heroku con:")
print("   heroku config:get OPENAI_API_KEY -a diario-oficial")
print("\nPara desarrollo local, necesitas una API key válida.")