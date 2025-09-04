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
    Mejorado para capturar mejor la información de hechos esenciales
    """
    if not texto_pdf or len(texto_pdf) < 100:
        return ""
    
    # Limpiar texto primero
    import re
    texto_limpio = re.sub(r'\s+', ' ', texto_pdf)  # Normalizar espacios
    
    # Buscar secciones clave en el PDF
    lineas = texto_pdf.split('\n')
    info_relevante = []
    lineas_agregadas = set()  # Para evitar duplicados
    
    # Palabras clave ampliadas y mejoradas
    palabras_clave = [
        'acuerdo', 'aprobó', 'decidió', 'resolvió', 'monto', 'precio',
        'millones', 'UF', '$', 'fecha', 'plazo', 'condiciones',
        'directorio', 'junta', 'accionistas', 'dividendo', 'utilidad',
        'capital', 'emisión', 'bonos', 'acciones', 'compra', 'venta',
        'fusión', 'división', 'reorganización', 'contrato', 'operación',
        'crédito', 'inversión', 'proyecto', 'renuncia', 'nombramiento',
        'gerente', 'director', 'cambio', 'modificación', 'aumento',
        'disminución', 'distribución', 'pago', 'vencimiento', 'tasa',
        'interés', 'colocación', 'suscripción', 'oferta', 'licitación',
        # Nuevas palabras clave para mejor captura
        'informo', 'comunico', 'anuncio', 'notifica', 'presenta',
        'porcentaje', '%', 'ejercicio', 'período', 'trimestre',
        'resultado', 'ingreso', 'gasto', 'activo', 'pasivo',
        'patrimonio', 'acción', 'título', 'valor', 'bolsa',
        'superintendencia', 'cmf', 'comisión', 'mercado', 'financiero'
    ]
    
    # Buscar también el cuerpo principal del mensaje
    inicio_cuerpo = False
    for i, linea in enumerate(lineas):
        linea_stripped = linea.strip()
        
        # Detectar inicio del cuerpo del mensaje
        if any(frase in linea.lower() for frase in ['de mi consideración', 'de nuestra consideración', 'presente', 'ref:']):
            inicio_cuerpo = True
        
        # Si estamos en el cuerpo, capturar las líneas importantes
        if inicio_cuerpo and i < 300:  # Limitar a las primeras 300 líneas
            if len(linea_stripped) > 20:  # Ignorar líneas muy cortas
                linea_lower = linea.lower()
                # Agregar líneas con palabras clave
                if any(palabra in linea_lower for palabra in palabras_clave):
                    # Incluir contexto ampliado (2 líneas antes y después)
                    for j in range(max(0, i-2), min(len(lineas), i+3)):
                        if j not in lineas_agregadas and len(lineas[j].strip()) > 10:
                            info_relevante.append(lineas[j])
                            lineas_agregadas.add(j)
        
        # También capturar líneas que empiezan con números o viñetas (típico de listas)
        elif re.match(r'^[\d\-•·]\s*\)', linea_stripped) or re.match(r'^\d+\.', linea_stripped):
            if i not in lineas_agregadas:
                info_relevante.append(linea)
                lineas_agregadas.add(i)
    
    # Si no encontramos mucha información relevante, tomar el cuerpo principal
    if len(info_relevante) < 5:
        # Buscar el texto después del saludo hasta antes de la despedida
        texto_cuerpo = []
        en_cuerpo = False
        for linea in lineas:
            if 'consideración' in linea.lower() or 'presente' in linea.lower():
                en_cuerpo = True
                continue
            if en_cuerpo:
                if any(despedida in linea.lower() for despedida in ['atentamente', 'cordialmente', 'saludos', 'sin otro particular']):
                    break
                if len(linea.strip()) > 10:
                    texto_cuerpo.append(linea)
        
        if texto_cuerpo:
            return '\n'.join(texto_cuerpo[:50])[:4000]  # Máximo 50 líneas o 4000 chars
    
    # Retornar la información relevante encontrada
    texto_relevante = '\n'.join(info_relevante)[:4000]
    return texto_relevante if texto_relevante else texto_pdf[:4000]

def generar_resumen_cmf_openai(entidad, materia, texto_pdf=None):
    """
    Genera un resumen usando OpenAI para hechos esenciales CMF
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    
    # VALIDACIÓN CRÍTICA: Si no hay texto PDF, no generar resúmenes inventados
    if not texto_pdf or len(texto_pdf.strip()) < 100:
        # Generar un resumen más informativo basado en la materia
        if "dividendo" in materia.lower():
            return f"{entidad} anunció {materia}. Los detalles específicos del dividendo no pudieron ser extraídos del documento."
        elif "cambios en la administración" in materia.lower():
            return f"{entidad} informó {materia}. Los nombres y cargos específicos no pudieron ser extraídos del documento."
        elif "junta" in materia.lower():
            return f"{entidad} convocó a {materia}. La fecha y agenda específica no pudieron ser extraídas del documento."
        elif "crédito" in materia.lower():
            return f"{entidad} informó sobre {materia}. Los montos y condiciones específicas no pudieron ser extraídos del documento."
        else:
            return f"{entidad} comunicó {materia}. No se pudo acceder al contenido del documento para mayor detalle."
    
    try:
        # Extraer información relevante del PDF
        info_relevante = extraer_informacion_relevante_pdf(texto_pdf)
        
        # Validar que tenemos información relevante
        if not info_relevante or len(info_relevante.strip()) < 50:
            return f"{entidad} comunicó {materia}. Documento sin información detallada disponible."
        
        # Preparar el contexto con información más específica
        contexto = f"Empresa: {entidad}\nTipo de hecho: {materia}\n\nContenido del documento:\n{info_relevante}"
        
        # Prompt mejorado y simplificado para mejor comprensión
        prompt = f"""Analiza este hecho esencial de la CMF chilena y genera un resumen profesional.

{contexto}

Instrucciones:
1. Lee cuidadosamente el contenido del documento proporcionado
2. Identifica la información más importante (montos, fechas, nombres, decisiones)
3. Genera un resumen claro y específico

Formato del resumen:
- Comienza con: "{entidad} [verbo de acción] ..."
- Verbos sugeridos: anunció, aprobó, informó, comunicó, acordó, designó, convocó
- Incluye datos específicos SI están en el documento (montos, fechas, nombres)
- Si no hay detalles específicos, describe la acción general
- Máximo 2-3 oraciones

Ejemplos de buenos resúmenes:
- "EMPRESA X aprobó el pago de dividendo definitivo de $45 por acción con cargo a utilidades 2024. El pago se realizará el 15 de mayo a accionistas inscritos."
- "EMPRESA Y designó a Pedro Pérez como nuevo gerente general en reemplazo de Juan González. El cambio será efectivo desde el 1 de abril."
- "EMPRESA Z acordó la emisión de bonos por UF 2.000.000 a 10 años plazo con tasa de 3,5% anual."

IMPORTANTE: Solo usa información que aparezca en el documento. No inventes datos."""

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
            
            # Validación final: detectar si el modelo está inventando o usando frases genéricas
            frases_prohibidas = [
                "no tengo acceso",
                "no puedo acceder",
                "lamentablemente",
                "juan pérez",
                "maría gonzález",
                "octubre de 2023",
                "noviembre de 2023",
                "15 de octubre",
                "1 de octubre",
                "20 de octubre",
                "no se especifican detalles",
                "no se especifica",
                "detalles adicionales"
            ]
            
            resumen_lower = resumen.lower()
            for frase in frases_prohibidas:
                if frase in resumen_lower:
                    # Crear resumen descriptivo profesional sin texto crudo
                    return f"{entidad} informó sobre {materia}. Consultar documento original en CMF para detalles completos."
            
            # Detectar patrones de invención
            import re
            # Si menciona fechas de 2023 que son inventadas
            if re.search(r'\b2023\b', resumen) and materia != "2023":
                return f"{entidad} comunicó {materia}. Información específica no disponible."
            
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
    
    # VALIDACIÓN CRÍTICA: Si no hay texto PDF, no generar resúmenes inventados
    if not texto_pdf or len(texto_pdf.strip()) < 100:
        # Usar los mismos mensajes informativos que OpenAI
        if "dividendo" in materia.lower():
            return f"{entidad} anunció {materia}. Los detalles específicos del dividendo no pudieron ser extraídos del documento."
        elif "cambios en la administración" in materia.lower():
            return f"{entidad} informó {materia}. Los nombres y cargos específicos no pudieron ser extraídos del documento."
        elif "junta" in materia.lower():
            return f"{entidad} convocó a {materia}. La fecha y agenda específica no pudieron ser extraídas del documento."
        elif "crédito" in materia.lower():
            return f"{entidad} informó sobre {materia}. Los montos y condiciones específicas no pudieron ser extraídos del documento."
        else:
            return f"{entidad} comunicó {materia}. No se pudo acceder al contenido del documento para mayor detalle."
    
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
- Si el documento no tiene información clara, indica que "no se especifican detalles en el documento"
- NUNCA inventes nombres como "Juan Pérez" o "María González"
- NUNCA digas "no tengo acceso" o "lamentablemente"
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
            
            # Validación final: detectar si el modelo está inventando o usando frases genéricas
            frases_prohibidas = [
                "no tengo acceso",
                "no puedo acceder",
                "lamentablemente",
                "juan pérez",
                "maría gonzález",
                "octubre de 2023",
                "noviembre de 2023",
                "15 de octubre",
                "1 de octubre",
                "20 de octubre",
                "no se especifican detalles",
                "no se especifica",
                "detalles adicionales"
            ]
            
            resumen_lower = resumen.lower()
            for frase in frases_prohibidas:
                if frase in resumen_lower:
                    # Crear resumen descriptivo profesional sin texto crudo
                    return f"{entidad} informó sobre {materia}. Consultar documento original en CMF para detalles completos."
            
            # Detectar patrones de invención
            import re
            # Si menciona fechas de 2023 que son inventadas
            if re.search(r'\b2023\b', resumen) and materia != "2023":
                return f"{entidad} comunicó {materia}. Información específica no disponible."
            
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