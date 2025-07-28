"""
Generador de resúmenes con IA para hechos esenciales CMF
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def generar_resumen_cmf_openai(entidad, materia, texto_pdf=None):
    """
    Genera un resumen usando OpenAI para hechos esenciales CMF
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        # Preparar el contexto
        contexto = f"Empresa: {entidad}\nMateria: {materia}"
        if texto_pdf and len(texto_pdf) > 100:
            contexto += f"\n\nDetalles del hecho:\n{texto_pdf[:3000]}"
        
        prompt = f"""Eres un analista financiero experto. Genera un resumen conciso (máximo 2 líneas) de este hecho esencial para inversionistas.

{contexto}

El resumen debe:
1. Explicar brevemente qué acción tomó la empresa
2. Mencionar el impacto potencial para inversionistas
3. Ser objetivo y profesional
4. NO incluir emojis ni caracteres especiales

Responde SOLO con el resumen, sin introducciones ni explicaciones adicionales."""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Eres un analista financiero experto en mercados chilenos."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            resumen = result['choices'][0]['message']['content'].strip()
            return resumen
        else:
            print(f"[OpenAI] Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"[OpenAI] Error generando resumen CMF: {str(e)}")
        return None

def generar_resumen_cmf_groq(entidad, materia, texto_pdf=None):
    """
    Genera un resumen usando Groq para hechos esenciales CMF
    """
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return None
    
    try:
        # Preparar el contexto
        contexto = f"Empresa: {entidad}\nMateria: {materia}"
        if texto_pdf and len(texto_pdf) > 100:
            contexto += f"\n\nDetalles del hecho:\n{texto_pdf[:2000]}"
        
        prompt = f"""Eres un analista financiero experto. Genera un resumen conciso (máximo 2 líneas) de este hecho esencial para inversionistas.

{contexto}

El resumen debe:
1. Explicar brevemente qué acción tomó la empresa
2. Mencionar el impacto potencial para inversionistas
3. Ser objetivo y profesional
4. NO incluir emojis ni caracteres especiales

Responde SOLO con el resumen, sin introducciones ni explicaciones adicionales."""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "system", "content": "Eres un analista financiero experto en mercados chilenos."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            resumen = result['choices'][0]['message']['content'].strip()
            return resumen
        else:
            print(f"[Groq] Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"[Groq] Error generando resumen CMF: {str(e)}")
        return None

def generar_resumen_cmf(entidad, materia, texto_pdf=None):
    """
    Genera un resumen con IA para hechos esenciales CMF.
    Intenta con OpenAI primero, luego con Groq.
    """
    # Intentar con OpenAI
    resumen = generar_resumen_cmf_openai(entidad, materia, texto_pdf)
    if resumen:
        return resumen
    
    # Si falla OpenAI, intentar con Groq
    resumen = generar_resumen_cmf_groq(entidad, materia, texto_pdf)
    if resumen:
        return resumen
    
    # Si todo falla, retornar un resumen básico
    return f"{entidad} - {materia}"