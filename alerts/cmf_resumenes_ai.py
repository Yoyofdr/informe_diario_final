"""
Generador de resúmenes con IA para hechos esenciales CMF
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def extraer_informacion_relevante_pdf(texto_pdf):
    """
    Extrae la información más relevante del PDF para generar un mejor resumen
    """
    if not texto_pdf or len(texto_pdf) < 100:
        return ""
    
    # Buscar secciones clave en el PDF
    lineas = texto_pdf.split('\n')
    info_relevante = []
    
    # Palabras clave que indican información importante
    palabras_clave = [
        'acuerdo', 'aprobó', 'decidió', 'resolvió', 'monto', 'precio',
        'millones', 'UF', '$', 'fecha', 'plazo', 'condiciones',
        'directorio', 'junta', 'accionistas', 'dividendo', 'utilidad',
        'capital', 'emisión', 'bonos', 'acciones', 'compra', 'venta',
        'fusión', 'división', 'reorganización', 'contrato', 'operación',
        'crédito', 'inversión', 'proyecto', 'renuncia', 'nombramiento',
        'gerente', 'director', 'cambio', 'modificación', 'aumento',
        'disminución', 'distribución', 'pago', 'vencimiento', 'tasa',
        'interés', 'colocación', 'suscripción', 'oferta', 'licitación'
    ]
    
    for i, linea in enumerate(lineas[:200]):  # Revisar las primeras 200 líneas
        linea_lower = linea.lower()
        if any(palabra in linea_lower for palabra in palabras_clave):
            # Incluir contexto (línea anterior y siguiente si existen)
            if i > 0:
                info_relevante.append(lineas[i-1])
            info_relevante.append(linea)
            if i < len(lineas) - 1:
                info_relevante.append(lineas[i+1])
    
    # Limitar a 4000 caracteres de información relevante
    texto_relevante = '\n'.join(info_relevante)[:4000]
    return texto_relevante if texto_relevante else texto_pdf[:4000]

def generar_resumen_cmf_openai(entidad, materia, texto_pdf=None):
    """
    Genera un resumen usando OpenAI para hechos esenciales CMF
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        # Extraer información relevante del PDF
        info_relevante = extraer_informacion_relevante_pdf(texto_pdf) if texto_pdf else ""
        
        # Preparar el contexto con información más específica
        contexto = f"Empresa: {entidad}\nTipo de hecho: {materia}"
        if info_relevante:
            contexto += f"\n\nInformación clave del documento:\n{info_relevante}"
        
        # Prompt mejorado para obtener información más específica
        prompt = f"""Eres un analista financiero senior especializado en el mercado chileno. Analiza este hecho esencial y genera un resumen ESPECÍFICO Y DETALLADO.

{contexto}

GENERA UN RESUMEN QUE INCLUYA:
1. La acción ESPECÍFICA tomada (con montos, fechas o porcentajes SOLO si están disponibles en el documento)
2. El impacto CONCRETO para los accionistas/inversionistas
3. Cualquier dato numérico relevante que aparezca en el documento

REGLAS CRÍTICAS - PROHIBIDO INVENTAR:
- SOLO menciona información que aparezca EXPLÍCITAMENTE en el documento proporcionado
- Si hay montos en el documento, inclúyelos
- Si hay fechas específicas en el documento, menciónalas
- Si hay nombres o porcentajes en el documento, especifícalos
- Si NO hay datos específicos, describe la acción sin inventar números
- NUNCA inventes montos, fechas, nombres o porcentajes que no estén en el texto
- NO uses frases genéricas como "comunicó información" o "presentó documentos"
- NO incluyas emojis ni caracteres especiales
- Máximo 3 líneas

Responde SOLO con el resumen basado ÚNICAMENTE en la información proporcionada."""

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
            "temperature": 0.2,
            "max_tokens": 200
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
        # Extraer información relevante del PDF  
        info_relevante = extraer_informacion_relevante_pdf(texto_pdf) if texto_pdf else ""
        
        # Preparar el contexto con información más específica
        contexto = f"Empresa: {entidad}\nTipo de hecho: {materia}"
        if info_relevante:
            contexto += f"\n\nInformación clave del documento:\n{info_relevante}"
        
        # Mismo prompt mejorado
        prompt = f"""Eres un analista financiero senior especializado en el mercado chileno. Analiza este hecho esencial y genera un resumen ESPECÍFICO Y DETALLADO.

{contexto}

GENERA UN RESUMEN QUE INCLUYA:
1. La acción ESPECÍFICA tomada (con montos, fechas o porcentajes SOLO si están disponibles en el documento)
2. El impacto CONCRETO para los accionistas/inversionistas
3. Cualquier dato numérico relevante que aparezca en el documento

REGLAS CRÍTICAS - PROHIBIDO INVENTAR:
- SOLO menciona información que aparezca EXPLÍCITAMENTE en el documento proporcionado
- Si hay montos en el documento, inclúyelos
- Si hay fechas específicas en el documento, menciónalas
- Si hay nombres o porcentajes en el documento, especifícalos
- Si NO hay datos específicos, describe la acción sin inventar números
- NUNCA inventes montos, fechas, nombres o porcentajes que no estén en el texto
- NO uses frases genéricas como "comunicó información" o "presentó documentos"
- NO incluyas emojis ni caracteres especiales
- Máximo 3 líneas

Responde SOLO con el resumen basado ÚNICAMENTE en la información proporcionada."""

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
            "temperature": 0.2,
            "max_tokens": 200
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