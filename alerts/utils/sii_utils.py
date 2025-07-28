"""
Utilidades para el manejo de contenido del Servicio de Impuestos Internos (SII)
Centraliza la lógica de detección, clasificación y constantes relacionadas con SII
"""

# ==================== CONSTANTES SII ====================

# Secciones oficiales del SII en el sistema
SECCIONES_SII = {
    'SII': 'SII',  # Sección general para contenido SII del Diario Oficial
    'SII_CIRCULARES': 'SERVICIO DE IMPUESTOS INTERNOS - CIRCULARES',
    'SII_RESOLUCIONES': 'SERVICIO DE IMPUESTOS INTERNOS - RESOLUCIONES',
    'SII_JURISPRUDENCIA': 'SERVICIO DE IMPUESTOS INTERNOS - JURISPRUDENCIA'
}

# Palabras clave para identificar contenido SII
PALABRAS_CLAVE_SII = {
    'generales': [
        'servicio de impuestos internos',
        'impuestos internos',
        ' sii ',
        'sii n°',
        'sii nº',
        'resolución exenta sii',
        'resolución ex sii',
        'resolución ex. sii',
        'circular sii',
        'circular n°',
        'circular nº'
    ],
    'tributarias': [
        'documentos tributarios electrónicos',
        'facturación electrónica',
        'boletas electrónicas',
        'impuesto a las ventas y servicios',
        'impuesto al valor agregado',
        'iva',
        'impuesto a la renta',
        'código tributario',
        'tributario',
        'tributaria',
        'impuesto',
        'contribuyente',
        'declaración',
        'formulario',
        'fiscalización',
        'renta'
    ],
    'administrativas': [
        'oficio ordinario',
        'jurisprudencia administrativa',
        'subdirección jurídica',
        'subdirección de fiscalización',
        'delega facultades'
    ]
}

# Palabras clave para excluir contenido no tributario
EXCLUSIONES_NO_TRIBUTARIAS = [
    'impacto ambiental',
    'declaración de impacto ambiental',
    'evaluación ambiental',
    'participación ciudadana',
    'proyecto eólico',
    'terminal de buses',
    'concesión marítima',
    'concesión de acuicultura'
]

# ==================== FUNCIONES DE DETECCIÓN ====================

def es_contenido_sii(titulo):
    """
    Determina si un título corresponde a contenido del SII basándose en palabras clave
    y criterios específicos del dominio tributario.
    
    Args:
        titulo (str): El título del documento a evaluar
        
    Returns:
        bool: True si es contenido SII, False en caso contrario
    """
    if not titulo:
        return False
        
    titulo_lower = titulo.lower()
    
    # Verificar criterios generales del SII
    for criterio in PALABRAS_CLAVE_SII['generales']:
        if criterio in titulo_lower:
            return True
    
    # Verificar si es resolución exenta con contenido tributario
    if 'resolución exenta' in titulo_lower:
        # Verificar que tenga contenido tributario
        tiene_contenido_tributario = any(
            criterio in titulo_lower 
            for criterio in PALABRAS_CLAVE_SII['tributarias']
        )
        
        # Verificar que no tenga exclusiones
        tiene_exclusiones = any(
            exclusion in titulo_lower 
            for exclusion in EXCLUSIONES_NO_TRIBUTARIAS
        )
        
        if tiene_contenido_tributario and not tiene_exclusiones:
            return True
    
    return False

def clasificar_tipo_documento_sii(titulo):
    """
    Clasifica el tipo de documento SII basándose en el título
    
    Args:
        titulo (str): El título del documento
        
    Returns:
        str: Tipo de documento ('circular', 'resolucion', 'jurisprudencia', 'general')
    """
    if not titulo:
        return 'general'
        
    titulo_lower = titulo.lower()
    
    if 'circular' in titulo_lower:
        return 'circular'
    elif 'resolución' in titulo_lower or 'resolucion' in titulo_lower:
        return 'resolucion'
    elif 'jurisprudencia' in titulo_lower or 'oficio' in titulo_lower:
        return 'jurisprudencia'
    else:
        return 'general'

def obtener_seccion_sii(tipo_documento):
    """
    Obtiene la sección SII correspondiente según el tipo de documento
    
    Args:
        tipo_documento (str): Tipo de documento SII
        
    Returns:
        str: Clave de la sección SII correspondiente
    """
    mapeo_secciones = {
        'circular': 'SII_CIRCULARES',
        'resolucion': 'SII_RESOLUCIONES',
        'jurisprudencia': 'SII_JURISPRUDENCIA',
        'general': 'SII'
    }
    
    return mapeo_secciones.get(tipo_documento, 'SII')

# ==================== FUNCIONES DE FORMATO ====================

def formatear_titulo_sii(tipo, numero, fecha):
    """
    Formatea el título de un documento SII de manera consistente
    
    Args:
        tipo (str): Tipo de documento (Circular, Resolución Exenta, etc.)
        numero (str): Número del documento
        fecha (str): Fecha del documento
        
    Returns:
        str: Título formateado
    """
    if tipo.lower() == 'circular':
        return f"Circular N° {numero} - {fecha}"
    elif 'resolución' in tipo.lower():
        return f"Resolución Exenta SII N° {numero} - {fecha}"
    elif 'jurisprudencia' in tipo.lower():
        return f"Jurisprudencia N° {numero} - {fecha}"
    else:
        return f"{tipo} N° {numero} - {fecha}"