"""
Criterios profesionales para análisis de hechos esenciales CMF
Basado en mejores prácticas de Bloomberg/Refinitiv
"""

# Empresas IPSA (actualizar semestralmente según cambios en el índice)
EMPRESAS_IPSA = {
    # Bancos
    "BANCO DE CHILE", "BANCO SANTANDER", "BANCO SANTANDER-CHILE", "BCI", "BANCO CREDITO", 
    "BANCO ITAU", "ITAU CORPBANCA", "SCOTIABANK",
    
    # Retail
    "CENCOSUD", "FALABELLA", "RIPLEY", "SMU", "FORUS",
    
    # Utilities
    "ENEL CHILE", "ENEL AMERICAS", "COLBUN", "ENGIE", "AGUAS ANDINAS",
    
    # Commodities y Materiales
    "SQM", "SQM-A", "SQM-B", "COPEC", "CMPC", "CAP", "MOLIBDENOS",
    
    # Inmobiliarias
    "PARQUE ARAUCO", "PLAZA", "MALL PLAZA", "CENCOSUD SHOPPING",
    
    # Telecomunicaciones
    "ENTEL", "WOM",
    
    # Transporte
    "VAPORES", "SONDA",
    
    # Otros
    "CCU", "EMBOTELLADORA ANDINA", "CONCHA Y TORO", "ILC", "SECURITY",
    "QUINENCO", "ORO BLANCO", "BESALCO"
}

# Empresas estratégicas adicionales (no IPSA pero relevantes)
EMPRESAS_ESTRATEGICAS = {
    # Aerolíneas y Transporte
    "LATAM AIRLINES", "LAN", "LATAM",  # Alta sensibilidad post-reestructuración
    "SKY AIRLINE", "JETSMART",
    
    # Grandes Holdings y Conglomerados
    "ILC",  # Inversiones La Construcción
    "CONSORCIO FINANCIERO",
    "GRUPO SECURITY",
    "GRUPO PATIO",
    "GRUPO ANGELINI",
    "GRUPO LUKSIC",
    
    # AFPs (altamente reguladas y sistémicas)
    "HABITAT",
    "CUPRUM",
    "PROVIDA",
    "CAPITAL",
    "MODELO",
    "PLANVITAL",
    "UNO",
    
    # Casinos y Entretenimiento
    "ENJOY",
    "DREAMS",
    "SUN MONTICELLO",
    "MARINA DEL SOL",
    
    # Constructoras e Inmobiliarias
    "SALFACORP",
    "SOCOVESA",
    "INGEVEC",
    "ECHEVERRIA IZQUIERDO",
    "PAZ CORP",
    "MOLLER",
    "ENACO",
    "FUNDAMENTA",
    "ALMAGRO",
    "MANQUEHUE",
    
    # Alimentos y Bebidas
    "CRISTALES",
    "CAROZZI",
    "WATTS",
    "MULTIFOODS",
    "AGROSUPER",
    "ARIZTIA",
    "DON POLLO",
    "TRENDY",
    "TUCAPEL",
    
    # Pesca y Acuicultura
    "BLUMAR",
    "CAMANCHACA",
    "AUSTRALIS SEAFOODS",
    "MULTIEXPORT",
    "VENTISQUEROS",
    "SALMONES ANTARTICA",
    "AQUACHILE",
    
    # Forestal
    "MASISA",
    "ARAUCO",
    
    # Retail adicional
    "TRICOT",
    "HITES",
    "LA POLAR",
    "ABCDIN",
    "CORONA",
    "JOHNSON",
    
    # Tecnología y Telecomunicaciones
    "VTR",
    "MOVISTAR",
    "CLARO",
    "MUNDO",
    "GTDINTERNET",
    
    # Salud
    "CLINICA LAS CONDES",
    "CLINICA ALEMANA",
    "CLINICA SANTA MARIA",
    "CLINICA DAVILA",
    "REDSALUD",
    "BANMEDICA",
    "CRUZ BLANCA",
    "COLMENA",
    "MASVIDA",
    "VIDA TRES",
    
    # Transporte y Logística
    "TRANSBANK",
    "REDBUS",
    "TURBUS",
    "PULLMAN",
    "SOTRASER",
    "PUERTO VENTANAS",
    "PUERTO LIRQUEN",
    
    # Educación
    "LAUREATE",
    "UNIVERSIDAD ANDRES BELLO",
    "UNIVERSIDAD LAS AMERICAS",
    "DUOC UC",
    "INACAP",
    
    # Energía renovables
    "ACCIONA",
    "MAINSTREAM",
    "PATTERN ENERGY",
    "AELA ENERGIA",
    
    # Servicios Financieros
    "FACTORING SECURITY",
    "TANNER",
    "FORUM",
    "COOPEUCH",
    
    # Otros sectores importantes
    "CODELCO",  # Aunque es estatal, sus emisiones de bonos son relevantes
    "METRO",  # Emisor frecuente de bonos
    "EFE",  # Empresa de Ferrocarriles
    "CORREOS DE CHILE"
}

# Categorías de hechos esenciales y sus palabras clave
CATEGORIAS_HECHOS = {
    "CRITICO": {
        "peso": 9,
        "keywords": [
            # Cambios de control
            "toma de control", "cambio de control", "opa", "oferta publica de adquisicion",
            "venta de control", "controlador", "adquisicion de control",
            
            # M&A
            "fusion", "adquisicion", "compra de empresa", "venta de filial", 
            "merger", "spin off", "division", "escision", "venta de activos estrategicos",
            
            # Profit warnings
            "profit warning", "advertencia de resultados", "deterioro significativo",
            "perdida significativa", "impacto negativo material", "revision a la baja",
            
            # Reestructuración financiera
            "reorganizacion judicial", "quiebra", "insolvencia", "default",
            "incumplimiento de covenant", "aceleracion de deuda", "cesacion de pagos",
            "reestructuracion de deuda", "reestructuracion financiera"
        ]
    },
    
    "IMPORTANTE": {
        "peso": 7.5,
        "keywords": [
            # Cambios en alta gerencia
            "renuncia gerente general", "renuncia ceo", "cambio gerente general",
            "cambio ceo", "renuncia cfo", "cambio cfo", "renuncia presidente",
            "cambio presidente directorio", "cambio de administracion",
            "nuevo gerente general", "nombra gerente general", "designa gerente general",
            "nombramiento gerente", "asume como gerente general",
            
            # Emisiones significativas
            "emisión de bonos", "emisión de acciones", "aumento de capital",
            "colocación de bonos", "programa de emisión", "emisión de deuda",
            "oferta de bonos", "oferta pública de bonos", "colocación exitosa",
            "colocación de valores", "colocación en mercados", "colocación internacional",
            # Sin tildes para compatibilidad
            "emision de bonos", "emision de acciones",
            "colocacion de bonos", "programa de emision", "emision de deuda",
            "colocacion de valores", "colocacion en mercados",
            
            # Contratos materiales
            "contrato material", "adjudicacion", "licitacion ganada",
            "joint venture", "alianza estrategica", "contrato significativo",
            "acuerdo comercial relevante", "contrato por usd", "contrato por uf",
            
            # Inversiones significativas
            "inversion significativa", "adquisicion de activos", "compra de propiedad",
            "proyecto de expansion", "nueva planta", "ampliacion de capacidad"
        ]
    },
    
    "MODERADO": {
        "peso": 5.5,
        "keywords": [
            # Resultados y juntas
            "fecu", "resultados trimestrales", "estados financieros",
            "junta de accionistas", "junta extraordinaria", "citacion a junta",
            "dividendo", "reparto de utilidades", "politica de dividendos",
            
            # Cambios menores
            "cambio de director", "renuncia de director", "nombramiento director",
            "cambio de ejecutivo", "modificacion estatutos", "reforma estatutos"
        ]
    },
    
    "RUTINARIO": {
        "peso": 2,
        "keywords": [
            # Procedimientos administrativos
            "cambio de domicilio", "cambio de direccion", "actualizacion de registro",
            "certificado", "inscripcion", "comunicacion de hecho", "fe de erratas",
            "rectificacion", "complemento", "aclaracion"
        ]
    }
}

def es_empresa_ipsa(nombre_empresa):
    """Verifica si la empresa pertenece al IPSA"""
    nombre_upper = nombre_empresa.upper().strip()
    for empresa_ipsa in EMPRESAS_IPSA:
        if empresa_ipsa in nombre_upper or nombre_upper in empresa_ipsa:
            return True
    return False

def es_empresa_estrategica(nombre_empresa):
    """Verifica si la empresa es estratégica (IPSA o adicional)"""
    if es_empresa_ipsa(nombre_empresa):
        return True
    
    nombre_upper = nombre_empresa.upper().strip()
    for empresa in EMPRESAS_ESTRATEGICAS:
        if empresa in nombre_upper or nombre_upper in empresa:
            return True
    return False

def evaluar_criticidad_hecho(titulo, materia, entidad):
    """
    Evalúa la criticidad de un hecho esencial basado en criterios profesionales
    
    Returns:
        tuple: (categoria, peso_base, es_prioritaria)
    """
    texto_completo = f"{titulo} {materia}".lower()
    es_prioritaria = es_empresa_estrategica(entidad)
    
    # Evaluar cada categoría
    for categoria, info in CATEGORIAS_HECHOS.items():
        for keyword in info["keywords"]:
            if keyword in texto_completo:
                return categoria, info["peso"], es_prioritaria
    
    # Por defecto es rutinario
    return "RUTINARIO", CATEGORIAS_HECHOS["RUTINARIO"]["peso"], es_prioritaria

def calcular_relevancia_profesional(titulo, materia, entidad, contexto_adicional=""):
    """
    Calcula la relevancia final usando criterios profesionales
    
    Args:
        titulo: Título del hecho esencial
        materia: Materia del hecho
        entidad: Nombre de la empresa
        contexto_adicional: Información adicional (montos, impactos, etc)
    
    Returns:
        tuple: (relevancia_final, categoria, es_ipsa)
    """
    categoria, peso_base, es_prioritaria = evaluar_criticidad_hecho(titulo, materia, entidad)
    es_ipsa = es_empresa_ipsa(entidad)
    
    # Relevancia base según categoría
    relevancia = peso_base
    
    # Bonus por ser empresa IPSA - Aumentado para asegurar inclusión
    if es_ipsa:
        relevancia += 2.5  # Aumentado de 1.5 a 2.5
        # Garantizar mínimo de 5.0 para empresas IPSA (para que pasen como moderados)
        relevancia = max(relevancia, 5.0)
    # Bonus menor por ser empresa estratégica no-IPSA
    elif es_prioritaria:
        relevancia += 0.8
    
    # Factores adicionales del contexto
    contexto_lower = contexto_adicional.lower()
    
    # Bonus por montos significativos
    if any(word in contexto_lower for word in ["millon", "billion", "significativo"]):
        if "usd" in contexto_lower or "dolares" in contexto_lower:
            relevancia += 0.5
    
    # Bonus por impacto en resultados
    if any(word in contexto_lower for word in ["ebitda", "utilidad", "margen"]):
        if any(word in contexto_lower for word in ["10%", "20%", "30%", "40%", "50%"]):
            relevancia += 0.5
    
    # Cap máximo de 10
    relevancia = min(relevancia, 10)
    
    return relevancia, categoria, es_ipsa

def obtener_prompt_profesional(titulo, materia, entidad, contenido, categoria, es_ipsa):
    """
    Genera un prompt especializado según la categoría del hecho y si es IPSA
    """
    tipo_empresa = "[Empresa IPSA]" if es_ipsa else ""
    
    prompt_base = f"""
    Analiza el siguiente Hecho Esencial de {entidad} {tipo_empresa}.
    
    CATEGORÍA DETECTADA: {categoria}
    
    Tu tarea es crear un resumen ejecutivo profesional considerando:
    
    1. RESUMEN CONCISO (2-4 frases):
       - Primera frase: El hecho principal y su impacto
       - Siguientes frases: Detalles clave, montos, plazos
       - Enfoque en lo que importa a inversionistas institucionales
    
    2. DATOS CLAVE A EXTRAER:
    """
    
    if categoria == "CRITICO":
        prompt_base += """
       - Tipo de transacción (OPA, fusión, venta, etc.)
       - Contrapartes involucradas
       - Valorización o precio si está disponible
       - Impacto esperado en la empresa
       - Timeline de la operación
       - Condiciones precedentes importantes
    """
    elif categoria == "IMPORTANTE":
        prompt_base += """
       - Cargo específico del cambio gerencial (si aplica)
       - Monto de la emisión (si aplica)
       - Uso de los fondos (si aplica)
       - Términos clave del contrato (si aplica)
       - Impacto esperado en operaciones
    """
    elif categoria == "MODERADO":
        prompt_base += """
       - Métricas financieras clave (ingresos, EBITDA, utilidad)
       - Variaciones respecto al período anterior
       - Fecha y tipo de junta (si aplica)
       - Monto de dividendo por acción (si aplica)
    """
    
    prompt_base += f"""
    
    3. RELEVANCIA PARA EL MERCADO:
       - Impacto esperado en el precio de la acción
       - Importancia para el sector
       - Precedentes o comparables si son relevantes
    
    FORMATO DE RESPUESTA:
    {{
        "resumen": "Resumen ejecutivo claro y profesional",
        "relevancia": número entre 1-10 (ya calculado: {categoria}),
        "datos_clave": {{
            "monto": "si aplica",
            "plazo": "si aplica",
            "impacto": "descripción del impacto"
        }}
    }}
    
    Título: {titulo}
    Materia: {materia}
    
    Contenido del documento:
    {contenido[:3000]}
    """
    
    return prompt_base

def get_icono_categoria(categoria):
    """Retorna el ícono según la categoría"""
    iconos = {
        "CRITICO": "🔴",
        "IMPORTANTE": "🟡", 
        "MODERADO": "🟢",
        "RUTINARIO": "⚪"
    }
    return iconos.get(categoria, "⚪")

def filtrar_hechos_profesional(hechos, max_hechos=12):
    """
    Filtra hechos esenciales según criterios profesionales
    Máximo 12 hechos, priorizando por relevancia
    
    Reglas de filtrado (según instrucciones de Kampala):
    - Máximo 12 hechos (NUNCA más)
    - 🔴 Críticos (9-10 pts) → Siempre incluir
    - 🟡 Importantes (7-8.9 pts) → Incluir si hay espacio
    - 🟢 Moderados (5-6.9 pts) → Solo si son IPSA
    - ⚪ Rutinarios (<5 pts) → NUNCA incluir
    - EXCLUIR todos los hechos relacionados con fondos
    """
    # Primero, filtrar hechos relacionados con fondos
    hechos_sin_fondos = []
    for hecho in hechos:
        titulo = hecho.get('titulo', '').lower()
        materia = hecho.get('materia', '').lower()
        entidad = hecho.get('entidad', '').lower()
        
        # Excluir si contiene palabras relacionadas con fondos
        es_fondo = any(palabra in titulo or palabra in materia or palabra in entidad 
                      for palabra in ['fondo', 'fondos', 'fund', 'funds', 'fip', 'fia', 
                                     'fondo de inversion', 'fondo mutuo', 'mutual fund',
                                     'investment fund', 'fondo inmobiliario'])
        
        if not es_fondo:
            hechos_sin_fondos.append(hecho)
        else:
            print(f"  → Excluido (es fondo): {hecho.get('entidad', '')} - {hecho.get('titulo', '')[:50]}...")
    
    # Calcular relevancia para cada hecho que no es fondo
    hechos_evaluados = []
    
    for hecho in hechos_sin_fondos:
        titulo = hecho.get('titulo', '')
        materia = hecho.get('materia', '')
        entidad = hecho.get('entidad', '')
        
        # Calcular relevancia usando la función existente
        relevancia, categoria, es_ipsa = calcular_relevancia_profesional(
            titulo, materia, entidad
        )
        
        # Agregar información de relevancia al hecho
        hecho_evaluado = hecho.copy()
        hecho_evaluado['relevancia_calculada'] = relevancia
        hecho_evaluado['categoria_relevancia'] = categoria
        hecho_evaluado['es_ipsa'] = es_ipsa
        
        hechos_evaluados.append(hecho_evaluado)
    
    # Separar por categorías según puntuación
    criticos = [h for h in hechos_evaluados if h['relevancia_calculada'] >= 9]
    importantes = [h for h in hechos_evaluados if 7 <= h['relevancia_calculada'] < 9]
    moderados = [h for h in hechos_evaluados if 5 <= h['relevancia_calculada'] < 7]
    rutinarios = [h for h in hechos_evaluados if h['relevancia_calculada'] < 5]
    
    # Construir lista final según reglas
    hechos_finales = []
    
    # 1. Incluir TODOS los críticos (siempre)
    criticos_ordenados = sorted(criticos, key=lambda x: x['relevancia_calculada'], reverse=True)
    hechos_finales.extend(criticos_ordenados)
    
    # 2. Incluir importantes si hay espacio
    espacio_restante = max_hechos - len(hechos_finales)
    if espacio_restante > 0:
        importantes_ordenados = sorted(importantes, key=lambda x: x['relevancia_calculada'], reverse=True)
        hechos_finales.extend(importantes_ordenados[:espacio_restante])
    
    # 3. Incluir moderados si hay espacio (solo IPSA según las reglas)
    espacio_restante = max_hechos - len(hechos_finales)
    if espacio_restante > 0:
        moderados_ipsa = [h for h in moderados if h['es_ipsa']]
        moderados_ipsa_ordenados = sorted(moderados_ipsa, key=lambda x: x['relevancia_calculada'], reverse=True)
        hechos_finales.extend(moderados_ipsa_ordenados[:espacio_restante])
    
    # 4. NUNCA incluir rutinarios (regla estricta)
    
    # Ordenar lista final por relevancia
    hechos_finales = sorted(hechos_finales, key=lambda x: x['relevancia_calculada'], reverse=True)
    
    # Asegurar que no excedemos el máximo
    hechos_finales = hechos_finales[:max_hechos]
    
    # Log de filtrado para transparencia
    print(f"\n=== Filtrado Profesional CMF ===")
    print(f"Total hechos originales: {len(hechos)}")
    print(f"- Excluidos por ser fondos: {len(hechos) - len(hechos_sin_fondos)}")
    print(f"- Críticos (9-10): {len(criticos)}")
    print(f"- Importantes (7-8.9): {len(importantes)}")
    print(f"- Moderados (5-6.9): {len(moderados)} (IPSA: {len([h for h in moderados if h['es_ipsa']])})")
    print(f"- Rutinarios (<5): {len(rutinarios)} [DESCARTADOS]")
    print(f"Total hechos seleccionados: {len(hechos_finales)}")
    print(f"================================\n")
    
    return hechos_finales

def aplicar_regla_dorada(hecho):
    """
    Aplica la regla dorada: "¿Le importaría esto a un inversionista institucional?"
    """
    relevancia = hecho.get('relevancia_calculada', 0)
    es_ipsa = hecho.get('es_ipsa', False)
    categoria = hecho.get('categoria_relevancia', 'RUTINARIO')
    
    # Un inversionista institucional se interesa en:
    # 1. Cualquier hecho crítico o importante (relevancia >= 7)
    # 2. Hechos moderados solo si son de empresas IPSA
    # 3. Nunca en hechos rutinarios
    
    if relevancia >= 7:
        return True
    elif relevancia >= 5 and es_ipsa:
        return True
    else:
        return False