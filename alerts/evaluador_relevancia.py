"""
Evaluador de relevancia basado en IA para publicaciones del Diario Oficial
"""
import os
import requests
from dotenv import load_dotenv

class EvaluadorRelevancia:
    """Evalúa la relevancia de publicaciones usando IA"""
    
    def __init__(self):
        load_dotenv()
        
        # Intentar con OpenAI primero (más potente y confiable)
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.use_openai = bool(self.openai_api_key)
        
        # Si no hay OpenAI, intentar con Groq (30 req/min gratis)
        if not self.use_openai:
            self.groq_api_key = os.environ.get('GROQ_API_KEY')
            self.use_groq = bool(self.groq_api_key)
        else:
            self.use_groq = False
        
        # Si no hay OpenAI ni Groq, intentar con DeepSeek
        if not self.use_openai and not self.use_groq:
            self.deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')
            # Temporalmente deshabilitado porque no tiene saldo
            self.use_deepseek = False  # bool(self.deepseek_api_key)
        else:
            self.use_deepseek = False
        
        # Si no hay ninguno anterior, intentar con Gemini
        if not self.use_openai and not self.use_groq and not self.use_deepseek:
            try:
                import google.generativeai as genai
                api_key = os.environ.get('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
                else:
                    self.model = None
            except ImportError:
                self.model = None
    
    def evaluar_relevancia(self, titulo, texto_pdf=None):
        """
        Evalúa si una publicación es relevante para incluir en el informe diario.
        Retorna: (es_relevante: bool, justificacion: str)
        """
        # Si hay OpenAI configurado, usarlo primero
        if self.use_openai:
            return self._evaluar_con_openai(titulo, texto_pdf)
        
        # Si no hay OpenAI pero sí Groq, usarlo
        if self.use_groq:
            return self._evaluar_con_groq(titulo, texto_pdf)
        
        # Si no hay Groq pero sí DeepSeek, usarlo
        if self.use_deepseek:
            return self._evaluar_con_deepseek(titulo, texto_pdf)
        
        # Si no hay DeepSeek pero sí Gemini, usarlo
        if hasattr(self, 'model') and self.model:
            return self._evaluar_con_gemini(titulo, texto_pdf)
        
        # Si no hay IA disponible, usar reglas
        return self._evaluar_con_reglas(titulo)
    
    def _evaluar_con_openai(self, titulo, texto_pdf=None):
        """Evalúa relevancia usando OpenAI API"""
        try:
            # Preparar el contexto
            contexto = f"Título: {titulo}"
            if texto_pdf and len(texto_pdf) > 100:
                contexto += f"\n\nPrimeras líneas del documento:\n{texto_pdf[:2000]}"
            
            prompt = f"""Eres un experto en análisis de normativas chilenas. Evalúa si la siguiente publicación del Diario Oficial es relevante para incluir en un informe diario que será leído por empresas y ciudadanos.

Una publicación es RELEVANTE si cumple TODOS estos criterios:
- Tiene alcance nacional o afecta a múltiples regiones
- Impacta a un sector económico completo o múltiples empresas
- Y además cumple alguno de estos:
  1. Crea o modifica leyes, decretos supremos o políticas públicas importantes
  2. Establece nuevos procedimientos o requisitos de cumplimiento obligatorio
  3. Modifica significativamente tarifas, precios o impuestos (no ajustes rutinarios)
  4. Establece medidas de emergencia nacionales
  5. Define estrategias nacionales de desarrollo
  6. Abre procesos de consulta ciudadana nacional
  7. Convoca a licitaciones públicas de gran envergadura (>1000 UF)
  8. Actualiza o establece programas de regulación ambiental o normas de emisión
  9. Define nuevos estándares ambientales o modifica los existentes
  10. Es emitido por el SII (Servicio de Impuestos Internos) - SIEMPRE relevante
  11. Es emitido por la CMF y afecta empresas IPSA o mercados regulados

Una publicación NO es relevante si:
1. Es un nombramiento o designación individual
2. Es una rectificación o fe de erratas
3. Afecta solo a una persona, empresa o localidad específica
4. Es un permiso o concesión individual
5. Es de alcance muy local o específico
6. Son ajustes rutinarios de precios (combustibles, kerosene)
7. Son medidas fitosanitarias locales o regionales
8. Afecta solo a beneficiarios de programas específicos
9. Es una resolución de alcance limitado a una región o comuna

{contexto}

Responde SOLO con:
RELEVANTE: [SÍ/NO]
RAZÓN: [Explicación en una línea]"""

            # Llamar a OpenAI API
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o-mini",  # Modelo más económico y rápido
                "messages": [
                    {"role": "system", "content": "Eres un experto en análisis de normativas chilenas."},
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
                respuesta = result['choices'][0]['message']['content'].strip()
                
                # Parsear respuesta
                es_relevante = "RELEVANTE: SÍ" in respuesta
                
                # Extraer razón
                if "RAZÓN:" in respuesta:
                    razon = respuesta.split("RAZÓN:")[-1].strip()
                else:
                    razon = "Evaluado por OpenAI"
                
                return es_relevante, razon
            else:
                print(f"[OpenAI] Error {response.status_code}: {response.text}")
                # Fallback a Groq si falla OpenAI
                if self.use_groq:
                    return self._evaluar_con_groq(titulo, texto_pdf)
                return self._evaluar_con_reglas(titulo)
                
        except Exception as e:
            print(f"[OpenAI] Error: {str(e)}")
            # Fallback a Groq si falla OpenAI
            if self.use_groq:
                return self._evaluar_con_groq(titulo, texto_pdf)
            return self._evaluar_con_reglas(titulo)
    
    def _evaluar_con_groq(self, titulo, texto_pdf=None):
        """Evalúa relevancia usando Groq API"""
        try:
            # Preparar el contexto
            contexto = f"Título: {titulo}"
            if texto_pdf and len(texto_pdf) > 100:
                contexto += f"\n\nPrimeras líneas del documento:\n{texto_pdf[:1500]}"
            
            prompt = f"""Eres un experto en análisis de normativas chilenas. Evalúa si la siguiente publicación del Diario Oficial es relevante para incluir en un informe diario que será leído por empresas y ciudadanos.

Una publicación es RELEVANTE si cumple TODOS estos criterios:
- Tiene alcance nacional o afecta a múltiples regiones
- Impacta a un sector económico completo o múltiples empresas
- Y además cumple alguno de estos:
  1. Crea o modifica leyes, decretos supremos o políticas públicas importantes
  2. Establece nuevos procedimientos o requisitos de cumplimiento obligatorio
  3. Modifica significativamente tarifas, precios o impuestos (no ajustes rutinarios)
  4. Establece medidas de emergencia nacionales
  5. Define estrategias nacionales de desarrollo
  6. Abre procesos de consulta ciudadana nacional
  7. Convoca a licitaciones públicas de gran envergadura (>1000 UF)
  8. Actualiza o establece programas de regulación ambiental o normas de emisión
  9. Define nuevos estándares ambientales o modifica los existentes
  10. Es emitido por el SII (Servicio de Impuestos Internos) - SIEMPRE relevante
  11. Es emitido por la CMF y afecta empresas IPSA o mercados regulados

Una publicación NO es relevante si:
1. Es un nombramiento o designación individual
2. Es una rectificación o fe de erratas
3. Afecta solo a una persona, empresa o localidad específica
4. Es un permiso o concesión individual
5. Es de alcance muy local o específico
6. Son ajustes rutinarios de precios (combustibles, kerosene)
7. Son medidas fitosanitarias locales o regionales
8. Afecta solo a beneficiarios de programas específicos
9. Es una resolución de alcance limitado a una región o comuna

{contexto}

Responde SOLO con:
RELEVANTE: [SÍ/NO]
RAZÓN: [Explicación en una línea]"""

            # Llamar a Groq API
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "mixtral-8x7b-32768",
                "messages": [
                    {"role": "system", "content": "Eres un experto en análisis de normativas chilenas."},
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
                respuesta = result['choices'][0]['message']['content'].strip()
                
                # Parsear respuesta
                es_relevante = "RELEVANTE: SÍ" in respuesta
                
                # Extraer razón
                if "RAZÓN:" in respuesta:
                    razon = respuesta.split("RAZÓN:")[-1].strip()
                else:
                    razon = "Evaluado por Groq AI"
                
                return es_relevante, razon
            else:
                print(f"[Groq] Error {response.status_code}: {response.text}")
                return self._evaluar_con_reglas(titulo)
                
        except Exception as e:
            print(f"[Groq] Error: {str(e)}")
            return self._evaluar_con_reglas(titulo)
    
    def _evaluar_con_deepseek(self, titulo, texto_pdf=None):
        """Evalúa relevancia usando DeepSeek API"""
        try:
            # Preparar el contexto
            contexto = f"Título: {titulo}"
            if texto_pdf and len(texto_pdf) > 100:
                contexto += f"\n\nPrimeras líneas del documento:\n{texto_pdf[:1500]}"
            
            prompt = f"""Eres un experto en análisis de normativas chilenas. Evalúa si la siguiente publicación del Diario Oficial es relevante para incluir en un informe diario que será leído por empresas y ciudadanos.

Una publicación es RELEVANTE si cumple TODOS estos criterios:
- Tiene alcance nacional o afecta a múltiples regiones
- Impacta a un sector económico completo o múltiples empresas
- Y además cumple alguno de estos:
  1. Crea o modifica leyes, decretos supremos o políticas públicas importantes
  2. Establece nuevos procedimientos o requisitos de cumplimiento obligatorio
  3. Modifica significativamente tarifas, precios o impuestos (no ajustes rutinarios)
  4. Establece medidas de emergencia nacionales
  5. Define estrategias nacionales de desarrollo
  6. Abre procesos de consulta ciudadana nacional
  7. Convoca a licitaciones públicas de gran envergadura (>1000 UF)
  8. Actualiza o establece programas de regulación ambiental o normas de emisión
  9. Define nuevos estándares ambientales o modifica los existentes
  10. Es emitido por el SII (Servicio de Impuestos Internos) - SIEMPRE relevante
  11. Es emitido por la CMF y afecta empresas IPSA o mercados regulados

Una publicación NO es relevante si:
1. Es un nombramiento o designación individual
2. Es una rectificación o fe de erratas
3. Afecta solo a una persona, empresa o localidad específica
4. Es un permiso o concesión individual
5. Es de alcance muy local o específico
6. Son ajustes rutinarios de precios (combustibles, kerosene)
7. Son medidas fitosanitarias locales o regionales
8. Afecta solo a beneficiarios de programas específicos
9. Es una resolución de alcance limitado a una región o comuna

{contexto}

Responde SOLO con:
RELEVANTE: [SÍ/NO]
RAZÓN: [Explicación en una línea]"""

            # Llamar a DeepSeek API
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Eres un experto en análisis de normativas chilenas."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 150
            }
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                respuesta = result['choices'][0]['message']['content'].strip()
                
                # Parsear respuesta
                es_relevante = "RELEVANTE: SÍ" in respuesta
                
                # Extraer razón
                if "RAZÓN:" in respuesta:
                    razon = respuesta.split("RAZÓN:")[-1].strip()
                else:
                    razon = "Evaluado por DeepSeek"
                
                return es_relevante, razon
            else:
                print(f"[DeepSeek] Error {response.status_code}: {response.text}")
                return self._evaluar_con_reglas(titulo)
                
        except Exception as e:
            print(f"[DeepSeek] Error: {str(e)}")
            return self._evaluar_con_reglas(titulo)
    
    def _evaluar_con_gemini(self, titulo, texto_pdf=None):
        """Evalúa relevancia usando Gemini (método original)"""
        try:
            contexto = f"Título: {titulo}"
            if texto_pdf and len(texto_pdf) > 100:
                contexto += f"\n\nPrimeras líneas del documento:\n{texto_pdf[:1500]}"
            
            prompt = f"""Eres un experto en análisis de normativas chilenas. Evalúa si la siguiente publicación del Diario Oficial es relevante para incluir en un informe diario que será leído por empresas y ciudadanos.

Una publicación es RELEVANTE si cumple TODOS estos criterios:
- Tiene alcance nacional o afecta a múltiples regiones
- Impacta a un sector económico completo o múltiples empresas
- Y además cumple alguno de estos:
  1. Crea o modifica leyes, decretos supremos o políticas públicas importantes
  2. Establece nuevos procedimientos o requisitos de cumplimiento obligatorio
  3. Modifica significativamente tarifas, precios o impuestos (no ajustes rutinarios)
  4. Establece medidas de emergencia nacionales
  5. Define estrategias nacionales de desarrollo
  6. Abre procesos de consulta ciudadana nacional
  7. Convoca a licitaciones públicas de gran envergadura (>1000 UF)
  8. Actualiza o establece programas de regulación ambiental o normas de emisión
  9. Define nuevos estándares ambientales o modifica los existentes
  10. Es emitido por el SII (Servicio de Impuestos Internos) - SIEMPRE relevante
  11. Es emitido por la CMF y afecta empresas IPSA o mercados regulados

Una publicación NO es relevante si:
1. Es un nombramiento o designación individual
2. Es una rectificación o fe de erratas
3. Afecta solo a una persona, empresa o localidad específica
4. Es un permiso o concesión individual
5. Es de alcance muy local o específico
6. Son ajustes rutinarios de precios (combustibles, kerosene)
7. Son medidas fitosanitarias locales o regionales
8. Afecta solo a beneficiarios de programas específicos
9. Es una resolución de alcance limitado a una región o comuna

{contexto}

Responde SOLO con:
RELEVANTE: [SÍ/NO]
RAZÓN: [Explicación en una línea]"""

            response = self.model.generate_content(prompt)
            respuesta = response.text.strip()
            
            # Parsear respuesta
            es_relevante = "RELEVANTE: SÍ" in respuesta
            
            # Extraer razón
            if "RAZÓN:" in respuesta:
                razon = respuesta.split("RAZÓN:")[-1].strip()
            else:
                razon = "Evaluado por IA"
            
            return es_relevante, razon
            
        except Exception as e:
            print(f"[IA] Error evaluando relevancia: {str(e)}")
            # Fallback a reglas si falla la IA
            return self._evaluar_con_reglas(titulo)
    
    def _evaluar_con_reglas(self, titulo):
        """Evaluación mejorada por reglas basada en los ejemplos proporcionados"""
        titulo_upper = titulo.upper()
        
        # Primero verificar exclusiones específicas
        exclusiones = [
            ("NOMBRA A DON", "Nombramiento individual"),
            ("NOMBRA A DOÑA", "Nombramiento individual"),
            ("DESIGNA A", "Designación individual"),
            ("ACEPTA RENUNCIA", "Renuncia individual"),
            ("RECTIFICA", "Rectificación menor"),
            ("FE DE ERRATAS", "Corrección menor"),
            ("OTORGA CONCESIÓN", "Concesión individual"),
            ("OTORGA PERMISO", "Permiso individual"),
            ("AUTORIZA A", "Autorización individual"),
            ("FIJA PRECIOS DE REFERENCIA Y PARIDAD PARA KEROSENE", "Ajuste rutinario de precios"),
            ("FIJA PRECIOS DE PARIDAD PARA COMBUSTIBLES", "Ajuste rutinario de precios"),
            ("MOSCA DEL MEDITERRÁNEO", "Medida fitosanitaria local"),
            ("REGULACIONES CUARENTENARIAS", "Medida fitosanitaria local"),
            ("BONOS DE INCENTIVO AL RETIRO", "Beneficio para grupo específico"),
            ("TRABAJADORES(AS) BENEFICIARIOS(AS)", "Afecta solo a beneficiarios específicos"),
            ("CONCURSO PÚBLICO PARA PROVEER CARGO", "Concurso para cargo público"),
            ("LLAMADO A CONCURSO PÚBLICO PARA PROVEER CARGO", "Concurso para cargo público"),
            ("CARGO DE TERCER NIVEL JERÁRQUICO", "Concurso para cargo público"),
            ("PROVEER CARGO", "Concurso para cargo público")
        ]
        
        for exclusion, razon in exclusiones:
            if exclusion in titulo_upper:
                # Excepciones para cargos de alto nivel
                if any(cargo in titulo_upper for cargo in ["MINISTRO", "SUBSECRETARIO", "DIRECTOR NACIONAL", "DEFENSOR NACIONAL"]):
                    continue  # No excluir si es cargo importante
                return False, razon
        
        # Criterios de alta relevancia - SOLO incluir si son de alcance nacional o muy importante
        criterios_relevancia = [
            # Licitaciones y concursos públicos para bienes, servicios y proyectos (NO cargos)
            (["LICITACIÓN PÚBLICA", "BASES DE LICITACIÓN", 
              "LLAMADO A LICITACIÓN", "LLAMA A LICITACIÓN",
              "CONCURSO PÚBLICO PARA LA ASIGNACIÓN", "PROYECTO HABILITACIÓN"], 
             "Proceso de contratación pública"),
            
            # Emergencias SOLO si son nacionales
            (["EMERGENCIA NACIONAL", "ESTADO DE CATÁSTROFE", "ESTADO DE EXCEPCIÓN"], 
             "Situación de emergencia nacional"),
            
            # Procedimientos SOLO si son de alcance general
            (["MANUAL DE PROCEDIMIENTOS NACIONAL", "ESTABLECE PROCEDIMIENTO GENERAL"], 
             "Establece nuevos procedimientos generales"),
            
            # Estrategias SOLO nacionales
            (["ESTRATEGIA NACIONAL", "CONSULTA CIUDADANA NACIONAL", "PLAN NACIONAL"], 
             "Proceso estratégico nacional"),
            
            # Tarifas SOLO si son de servicios básicos o impacto general
            (["FIJA TARIFAS ELÉCTRICAS", "FÓRMULAS TARIFARIAS", "PRECIOS DE NUDO"], 
             "Fijación de tarifas de servicios básicos"),
            
            # Leyes y decretos supremos importantes
            (["LEY NÚM", "LEY N°", "DECRETO SUPREMO N°"], 
             "Norma de alto nivel"),
            
            # Modificaciones de leyes importantes
            (["MODIFICA LEY", "MODIFICA CÓDIGO"], 
             "Modificación legal importante"),
            
            # Creación de entidades nacionales
            (["CREACIÓN DE", "CREA NUEVO"], 
             "Creación institucional"),
            
            # Políticas públicas nacionales
            (["POLÍTICA NACIONAL", "PLAN NACIONAL", "PROGRAMA NACIONAL"], 
             "Política pública nacional"),
            
            # Medidas económicas de impacto general
            (["TIPO DE CAMBIO", "VALOR DE LA UF", "VALOR DEL DÓLAR", "MODIFICA IMPUESTO"], 
             "Medida económica de impacto general"),
            
            # Subsidios habitacionales y vivienda
            (["SUBSIDIO", "CRÉDITOS HIPOTECARIOS", "VIVIENDAS NUEVAS", "TASA DE INTERÉS"], 
             "Subsidio habitacional o medida de vivienda"),
            
            # Estándares de construcción y programas habitacionales
            (["ESTÁNDAR TÉCNICO", "PROGRAMA DE HABITABILIDAD", "CONSTRUCCIONES RURALES", "VIVIENDAS INDUSTRIALIZADAS"], 
             "Normativa técnica de construcción"),
            
            # Proyectos de infraestructura y servicios públicos
            (["SERVICIOS DE TELECOMUNICACIONES", "PROYECTO HABILITACIÓN", "FONDO DE DESARROLLO", 
              "SERVICIOS PÚBLICOS", "INFRAESTRUCTURA"], 
             "Proyecto de infraestructura o servicios públicos"),
            
            # Tipos de cambio (siempre relevante)
            (["TIPOS DE CAMBIO", "PARIDADES DE MONEDAS"], 
             "Información cambiaria"),
            
            # Regulaciones ambientales y programas de regulación
            (["PROGRAMA DE REGULACIÓN AMBIENTAL", "NORMAS DE EMISIÓN", "NORMAS DE CALIDAD AMBIENTAL",
              "PLANES DE DESCONTAMINACIÓN", "EVALUACIÓN AMBIENTAL", "IMPACTO AMBIENTAL",
              "ESTÁNDARES AMBIENTALES", "REGULACIÓN AMBIENTAL"], 
             "Regulación o programa ambiental"),
            
            # SII - Servicio de Impuestos Internos (SIEMPRE relevante)
            (["SERVICIO DE IMPUESTOS INTERNOS", "SII", "DIRECTOR NACIONAL DEL SERVICIO DE IMPUESTOS",
              "CIRCULAR SII", "RESOLUCIÓN SII", "OFICIO SII", "TRIBUTARIO", "TRIBUTARIA",
              "CÓDIGO TRIBUTARIO", "IMPUESTO A LA RENTA", "IVA", "FACTURA ELECTRÓNICA",
              "DOCUMENTOS TRIBUTARIOS", "FISCALIZACIÓN TRIBUTARIA", "CONTRIBUYENTES",
              "DECLARACIÓN DE IMPUESTOS", "DEVOLUCIÓN DE IMPUESTOS", "CONDONACIÓN",
              "NORMAS TRIBUTARIAS", "INTERPRETACIÓN TRIBUTARIA"], 
             "Normativa tributaria del SII"),
            
            # CMF - Comisión para el Mercado Financiero (empresas importantes)
            (["COMISIÓN PARA EL MERCADO FINANCIERO", "CMF", "SUPERINTENDENCIA DE VALORES",
              "SUPERINTENDENCIA DE BANCOS", "SUPERINTENDENCIA DE PENSIONES", "AFP",
              "BOLSA DE COMERCIO", "BOLSA DE VALORES", "OFERTA PÚBLICA", "EMISIÓN DE BONOS",
              "VALORES DE OFERTA PÚBLICA", "SOCIEDADES ANÓNIMAS ABIERTAS", "IPSA",
              "MERCADO DE VALORES", "MERCADO FINANCIERO", "INSTITUCIONES FINANCIERAS",
              "COMPAÑÍAS DE SEGUROS", "ADMINISTRADORAS DE FONDOS"], 
             "Regulación del mercado financiero (CMF)")
        ]
        
        # Evaluar cada criterio
        for palabras_clave, descripcion in criterios_relevancia:
            if any(palabra in titulo_upper for palabra in palabras_clave):
                # Verificaciones adicionales para ciertos casos
                if "EXTRACTO" in titulo_upper and "LICITACIÓN" not in titulo_upper:
                    continue  # Los extractos generalmente no son relevantes excepto licitaciones
                
                if "MUNICIPALIDAD DE" in titulo_upper or "COMUNA DE" in titulo_upper:
                    # Solo relevante si es creación de comuna o algo de alcance general
                    if "CREACIÓN" not in titulo_upper and "APRUEBA PLAN" not in titulo_upper:
                        continue
                
                # Verificación adicional: debe ser de alcance nacional
                if any(local in titulo_upper for local in ["REGIÓN", "REGIONAL", "COMUNA", "COMUNAL", "PROVINCIA", "PROVINCIAL"]):
                    # A menos que sea una emergencia o creación
                    if not any(excep in titulo_upper for excep in ["EMERGENCIA", "CREACIÓN", "ESTADO DE"]):
                        continue
                
                return True, descripcion
        
        # Si contiene "LEY" y modifica algo importante
        if " LEY " in titulo_upper and any(mod in titulo_upper for mod in ["MODIFICA", "ESTABLECE", "CREA"]):
            return True, "Ley que establece cambios importantes"
        
        # Por defecto, no relevante
        return False, "No cumple criterios de relevancia general"