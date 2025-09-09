#!/usr/bin/env python3
"""
Generador de resúmenes con IA para proyectos ambientales del SEA
Usa OpenAI para crear resúmenes ejecutivos concisos
"""

import os
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)

def generar_resumen_sea_openai(titulo: str, resumen_original: str, empresa: str = None, 
                               region: str = None, inversion: str = None) -> Optional[str]:
    """
    Genera un resumen ejecutivo conciso usando OpenAI para proyectos SEA
    
    Args:
        titulo: Título del proyecto
        resumen_original: Resumen original extraído del SEA
        empresa: Empresa titular del proyecto
        region: Región donde se desarrolla
        inversion: Monto de inversión
        
    Returns:
        Resumen ejecutivo generado con IA o None si falla
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.warning("No se encontró OPENAI_API_KEY")
        return None
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Preparar contexto adicional
        contexto = []
        if empresa:
            contexto.append(f"Empresa: {empresa}")
        if region:
            contexto.append(f"Región: {region}")
        if inversion:
            contexto.append(f"Inversión: {inversion}")
        
        contexto_str = ". ".join(contexto) if contexto else ""
        
        # Limitar el texto del resumen original para no exceder tokens
        resumen_truncado = resumen_original[:3000] if len(resumen_original) > 3000 else resumen_original
        
        prompt = f"""Eres un experto en análisis de proyectos ambientales en Chile.
        
Genera un resumen ejecutivo ULTRA CONCISO (máximo 3 líneas) del siguiente proyecto ambiental.
El resumen debe capturar SOLO la esencia del proyecto: qué es, su objetivo principal y el impacto esperado.

Proyecto: {titulo}
{contexto_str}

Resumen original del SEA:
{resumen_truncado}

IMPORTANTE:
- Máximo 3 líneas
- Enfócate en: tipo de proyecto, capacidad/magnitud si aplica, y objetivo principal
- NO incluyas detalles técnicos menores
- NO repitas información del título
- Usa lenguaje profesional y directo
- Si es un proyecto de energía, menciona la capacidad en MW
- Si es minero, menciona el mineral y producción estimada
- Si es inmobiliario, menciona número de unidades

Resumen ejecutivo:"""

        # Usar el modelo más económico para resúmenes
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un analista ambiental experto. Generas resúmenes ejecutivos ultra concisos y profesionales."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3,
            timeout=10
        )
        
        resumen = response.choices[0].message.content.strip()
        
        # Validar que el resumen no sea demasiado largo
        if len(resumen) > 500:
            # Tomar solo las primeras 3 oraciones
            oraciones = resumen.split('. ')[:3]
            resumen = '. '.join(oraciones)
            if not resumen.endswith('.'):
                resumen += '.'
        
        logger.info(f"✅ Resumen SEA generado con OpenAI ({len(resumen)} caracteres)")
        return resumen
        
    except Exception as e:
        logger.error(f"Error generando resumen SEA con OpenAI: {e}")
        return None


def generar_resumen_sea(titulo: str, resumen_original: str, empresa: str = None,
                        region: str = None, inversion: str = None) -> str:
    """
    Genera un resumen ejecutivo para proyectos SEA.
    Intenta usar IA, si falla retorna un resumen simplificado.
    
    Args:
        titulo: Título del proyecto
        resumen_original: Resumen original del SEA
        empresa: Empresa titular
        region: Región del proyecto
        inversion: Monto de inversión
        
    Returns:
        Resumen ejecutivo generado
    """
    # Intentar con OpenAI
    resumen_ia = generar_resumen_sea_openai(titulo, resumen_original, empresa, region, inversion)
    if resumen_ia:
        return resumen_ia
    
    # Fallback: retornar primeras líneas del resumen original
    if resumen_original:
        # Tomar primeros 400 caracteres o hasta el primer punto
        if len(resumen_original) > 400:
            # Buscar el primer punto después de 200 caracteres
            idx_punto = resumen_original.find('.', 200)
            if idx_punto > 0 and idx_punto < 400:
                return resumen_original[:idx_punto + 1]
            else:
                return resumen_original[:397] + "..."
        return resumen_original
    
    # Fallback final: resumen básico
    resumen = f"Proyecto ambiental"
    if empresa:
        resumen += f" de {empresa}"
    if region:
        resumen += f" en {region}"
    if inversion:
        resumen += f". Inversión: {inversion}"
    
    return resumen