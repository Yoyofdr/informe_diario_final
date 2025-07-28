import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from io import BytesIO
from pdfminer.high_level import extract_text
from pdf2image import convert_from_bytes
import pytesseract
import PyPDF2
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import time
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from alerts.services.cache_service import cache_service
from alerts.services.pdf_extractor import PDFExtractor
from alerts.utils.rate_limiter import rate_limited
from alerts.utils.retry_utils import retry
from django.core.mail import send_mail
from alerts.evaluador_relevancia import EvaluadorRelevancia
from alerts.utils.sii_utils import es_contenido_sii

BASE_URL = "https://www.diariooficial.interior.gob.cl/edicionelectronica/index.php"

SECCIONES_VALIDAS = [
    "NORMAS GENERALES",
    "NORMAS PARTICULARES",
    "AVISOS DESTACADOS",
    "Normas Generales",
    "Normas Particulares",
    "Avisos Destacados"
]

# Inicializar evaluador de relevancia con IA
evaluador_relevancia = EvaluadorRelevancia()

def es_licitacion_publica(titulo):
    """Detecta si es una licitación pública basándose en palabras clave."""
    titulo_lower = titulo.lower()
    palabras_licitacion = [
        'licitación', 'concurso público', 'bases de licitación',
        'llamado a licitación', 'propuesta pública', 'contratación pública'
    ]
    return any(palabra in titulo_lower for palabra in palabras_licitacion)

pdf_extractor = PDFExtractor()

@rate_limited
@retry(max_retries=3, backoff_factor=2)
def descargar_pdf_con_cache(url_pdf):
    """Descarga un PDF usando caché y rate limiting"""
    if url_pdf.startswith('http'):
        url_completa = url_pdf
    else:
        url_completa = f"https://www.diariooficial.interior.gob.cl{url_pdf}"
    # Intentar obtener del caché
    content = cache_service.get_pdf_content(url_completa)
    if content:
        return content
    # Descargar y guardar en caché
    resp = requests.get(url_completa, timeout=20)
    resp.raise_for_status()
    cache_service.set_pdf_content(url_completa, resp.content)
    return resp.content

def extraer_texto_pdf_mixto(url_pdf):
    """
    Extrae texto de un PDF usando caché y extractor robusto.
    """
    try:
        pdf_content = descargar_pdf_con_cache(url_pdf)
        if not pdf_content:
            print(f"[WARNING] No se pudo descargar el PDF: {url_pdf}")
            return ""
        
        texto, metodo = pdf_extractor.extract_text(pdf_content, max_pages=8)
        # print(f"[ExtractorRobusto] Método: {metodo}, Texto extraído: {texto[:500]}")
        return texto
    except Exception as e:
        print(f"[WARNING] Error extrayendo texto del PDF {url_pdf}: {str(e)}")
        return ""

def resumen_con_gemini(texto, titulo=None):
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key or not texto or len(texto) < 40:
        # print('[Gemini] No hay API key o el texto es muy corto.')
        return None
    try:
        # Limitar el texto al primer párrafo relevante (hasta el primer salto doble de línea o 800 caracteres)
        primer_parrafo = texto.split('\n\n')[0]
        if len(primer_parrafo) < 40:
            primer_parrafo = texto[:1200]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Resume este documento oficial chileno de forma muy concisa.\n\n"
            "INSTRUCCIONES:\n"
            "1. MÁXIMO 2 ORACIONES (60-80 palabras total).\n"
            "2. Incluye SOLO lo esencial:\n"
            "   - De qué trata el documento\n"
            "   - Quién lo emite y a quién afecta\n"
            "   - Fecha/plazo clave si existe\n"
            "3. Sé extremadamente conciso y directo.\n\n"
            f"Título: {titulo}\n"
            f"Texto: {primer_parrafo}"
        )
        # print('\n[Gemini] Texto enviado a Gemini:\n', primer_parrafo[:1000], '\n---')
        response = model.generate_content(prompt)
        # print('[Gemini] Respuesta cruda:', response.text)
        resumen = response.text.strip()
        
        # Limpiar el resumen de posibles saltos de línea o espacios extras
        resumen = ' '.join(resumen.split())
        
        # Asegurar que termine en punto
        if resumen and not resumen.endswith('.'):
            resumen += '.'
        
        return resumen if resumen else "No se pudo generar un resumen del documento."
    except Exception as e:
        # print('[Gemini] Error:', e)
        pass
    return None

def resumen_con_openai(texto, titulo=None):
    """Genera resúmenes usando OpenAI API"""
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or not texto or len(texto) < 40:
        return None
    
    try:
        # Limitar el texto al primer párrafo relevante (hasta el primer salto doble de línea o 1000 caracteres)
        primer_parrafo = texto.split('\n\n')[0]
        if len(primer_parrafo) < 40:
            primer_parrafo = texto[:1500]
        
        # Preparar la solicitud a OpenAI
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = (
            "Resume este documento oficial chileno de forma muy concisa.\n\n"
            "INSTRUCCIONES:\n"
            "1. MÁXIMO 2 ORACIONES (60-80 palabras total).\n"
            "2. Incluye SOLO lo esencial:\n"
            "   - De qué trata el documento\n"
            "   - Quién lo emite y a quién afecta\n"
            "   - Fecha/plazo clave si existe\n"
            "3. Sé extremadamente conciso y directo.\n\n"
            f"Título: {titulo}\n"
            f"Texto: {primer_parrafo}"
        )
        
        data = {
            "model": "gpt-4o-mini",  # Modelo más económico y rápido
            "messages": [
                {"role": "system", "content": "Eres un experto en resumir documentos oficiales chilenos de forma extremadamente concisa."},
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
            
            # Limpiar el resumen de posibles saltos de línea o espacios extras
            resumen = ' '.join(resumen.split())
            
            # Asegurar que termine en punto
            if resumen and not resumen.endswith('.'):
                resumen += '.'
            
            return resumen if resumen else "No se pudo generar un resumen del documento."
        else:
            print(f"[OpenAI] Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"[OpenAI] Error generando resumen: {str(e)}")
        return None

def resumen_con_huggingface(texto, titulo=None):
    from dotenv import load_dotenv
    load_dotenv()
    api_token = os.environ.get('HF_API_TOKEN')
    if not api_token or not texto or len(texto) < 40:
        return None
    endpoint = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
    headers = {"Authorization": f"Bearer {api_token}"}
    prompt = (
        f"<|system|>\nEres un asistente experto en explicar normas oficiales en lenguaje simple. Resume en máximo 3 frases, en español claro y directo, el hecho principal y su consecuencia práctica. No repitas el título ni el número de decreto, ni copies frases textuales del título. No cites normas, leyes, artículos ni uses frases como 'de acuerdo a', 'según', 'conforme a', 'establecido en', 'dispuesto en', 'n°', 'decreto', 'ley', 'artículo', 'constitución', 'reglamento', 'norma', 'regula', 'texto refundido'. Explica solo el hecho principal y su consecuencia. Ejemplo: 'Se nombra a un nuevo representante en la Comisión Chilena del Cobre, quien participará en la toma de decisiones de la entidad.'\n<|user|>\nTítulo: {titulo}\nTexto: {texto[:3000]}\n<|assistant|>"
    )
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 80}}
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        resumen = None
        if isinstance(data, list) and len(data) > 0 and 'generated_text' in data[0]:
            resumen = data[0]['generated_text']
        elif isinstance(data, dict) and 'generated_text' in data:
            resumen = data['generated_text']
        if resumen:
            resumen = resumen.strip()
            if '<|assistant|>' in resumen:
                resumen = resumen.split('<|assistant|>')[-1].strip()
            # Filtrar repeticiones del título y referencias legales
            frases = [f.strip() for f in resumen.split('.') if f.strip()]
            frases_filtradas = []
            for f in frases:
                if titulo and (f.lower().startswith(titulo.lower()) or f.lower() in titulo.lower()):
                    continue
                if any(pal in f.lower() for pal in ["artículo", "constitución", "ley", "decreto", "n°", "según", "conforme a", "de acuerdo a", "de acuerdo con", "dispuesto en", "establecido en", "reglamento", "norma", "regula", "texto refundido"]):
                    continue
                frases_filtradas.append(f)
            resumen = '. '.join(frases_filtradas[:3])
            if resumen and not resumen.endswith('.'):
                resumen += '.'
            return resumen
    except Exception as e:
        # print('[HF] Error:', e)
        pass
    return None

def generar_resumen_desde_texto(texto, titulo=None):
    # Intentar primero con OpenAI
    resumen_ia = resumen_con_openai(texto, titulo)
    if resumen_ia:
        return resumen_ia
    
    # Si falla OpenAI, intentar con Gemini
    resumen_ia = resumen_con_gemini(texto, titulo)
    if resumen_ia:
        return resumen_ia
    
    if not texto:
        return "No se pudo extraer el contenido del documento."
    return "No se pudo generar un resumen relevante."

def extraer_valores_dolar_euro(texto):
    """
    Extrae el valor del dólar observado (o DÓLAR EE.UU.) y del euro desde el texto del PDF del Banco Central.
    Retorna un dict: {'dolar': valor, 'euro': valor}
    """
    import re
    # print("\n--- TEXTO EXTRAÍDO DEL PDF PARA MONEDAS ---\n")
    # print(texto)
    # print("\n--- FIN DEL TEXTO EXTRAÍDO ---\n")
    resultado = {'dolar': None, 'euro': None}
    # Buscar DÓLAR EE.UU. (formato tabla actual)
    match_dolar = re.search(r'D[ÓO]LAR\s*EE\.?UU\.?\s*\*?\s*([\d\.,]+)', texto, re.IGNORECASE)
    if not match_dolar:
        # Fallback: DÓLAR OBSERVADO (formato antiguo)
        match_dolar = re.search(r'D[ÓO]LAR OBSERVADO[\s\*]*:?\s*\$?([\d\.,]+)', texto, re.IGNORECASE)
    if match_dolar:
        resultado['dolar'] = match_dolar.group(1).replace('.', '').replace(',', '.')
    # Buscar EURO (formato tabla actual)
    match_euro = re.search(r'EURO\s*([\d\.,]+)', texto, re.IGNORECASE)
    if match_euro:
        resultado['euro'] = match_euro.group(1).replace('.', '').replace(',', '.')
    # print("[DEBUG] Resultado extracción monedas:", resultado)
    return resultado

def obtener_numero_edicion(fecha, driver=None):
    """
    Obtiene el número de edición para una fecha específica del Diario Oficial.
    Versión mejorada que detecta automáticamente la edición correcta.
    """
    print(f"[EDITION] Buscando número de edición para fecha: {fecha}")
    
    # Primero intentar con caché local
    try:
        import json
        cache_file = os.path.join(os.path.dirname(__file__), '..', 'edition_cache.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache = json.load(f)
                if fecha in cache:
                    edition = cache[fecha]
                    print(f"[EDITION] Número de edición encontrado en caché: {edition}")
                    return edition
    except Exception as e:
        print(f"[EDITION] Error leyendo caché: {e}")
    
    # Si no está en caché, usar Selenium para detectar automáticamente
    driver_temporal = False
    driver_creado = driver
    
    try:
        if driver_creado is None:
            driver_temporal = True
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            # Agregar user agent para evitar detección
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            driver_creado = webdriver.Chrome(service=service, options=options)
            driver_creado.set_page_load_timeout(30)
        
        # Convertir fecha al formato que usa la URL (YYYY/MM/DD)
        dia, mes, anio = fecha.split('-')
        
        # Estrategia 1: Ir directamente a la URL de la fecha sin edición
        url_fecha = f"https://www.diariooficial.interior.gob.cl/publicaciones/{anio}/{mes}/{dia}/"
        print(f"[EDITION] Navegando a: {url_fecha}")
        driver_creado.get(url_fecha)
        time.sleep(3)
        
        # Buscar el selector de ediciones
        try:
            from selenium.webdriver.support.ui import WebDriverWait, Select
            from selenium.webdriver.support import expected_conditions as EC
            
            # Esperar a que el selector de ediciones esté presente
            edition_select_element = WebDriverWait(driver_creado, 10).until(
                EC.presence_of_element_located((By.ID, "ediciones"))
            )
            
            # Obtener la opción seleccionada
            select = Select(edition_select_element)
            selected_option = select.first_selected_option
            
            # El value contiene la URL completa con la edición
            selected_value = selected_option.get_attribute("value")
            print(f"[EDITION] Valor seleccionado: {selected_value}")
            
            # Extraer el número de edición de la URL
            import re
            match = re.search(r'/edicion-(\d+)/?', selected_value)
            if match:
                edition_number = match.group(1)
                print(f"[EDITION] Número de edición detectado: {edition_number}")
                
                # Actualizar el caché
                try:
                    cache_file = os.path.join(os.path.dirname(__file__), '..', 'edition_cache.json')
                    cache = {}
                    if os.path.exists(cache_file):
                        with open(cache_file, 'r') as f:
                            cache = json.load(f)
                    
                    cache[fecha] = edition_number
                    
                    with open(cache_file, 'w') as f:
                        json.dump(cache, f, indent=2)
                    
                    print(f"[EDITION] Caché actualizado con {fecha}: {edition_number}")
                except Exception as e:
                    print(f"[EDITION] Error actualizando caché: {e}")
                
                if driver_temporal:
                    driver_creado.quit()
                return edition_number
                
        except Exception as e:
            print(f"[EDITION] No se encontró selector de ediciones: {e}")
        
        # Estrategia 2: Buscar en el HTML actual si ya estamos en una página con edición
        current_url = driver_creado.current_url
        import re
        match = re.search(r'/edicion-(\d+)/?', current_url)
        if match:
            edition_number = match.group(1)
            print(f"[EDITION] Edición detectada en URL actual: {edition_number}")
            if driver_temporal:
                driver_creado.quit()
            return edition_number
        
        # Estrategia 3: Buscar publicaciones para verificar si hay contenido
        publicaciones = driver_creado.find_elements(By.CLASS_NAME, "light")
        if publicaciones:
            print(f"[EDITION] Se encontraron {len(publicaciones)} publicaciones")
        
        print("[EDITION] No se pudo detectar el número de edición automáticamente")
        
        if driver_temporal:
            driver_creado.quit()
        
        # Como último recurso, usar estimación basada en días hábiles
        return estimar_edicion_por_dias_habiles(fecha)
        
    except Exception as e:
        print(f"[EDITION] Error obteniendo número de edición: {str(e)}")
        if driver_temporal and driver_creado:
            try:
                driver_creado.quit()
            except:
                pass
        return estimar_edicion_por_dias_habiles(fecha)

def estimar_edicion_por_dias_habiles(fecha):
    """
    Estima el número de edición basándose en días hábiles con validaciones mejoradas.
    """
    try:
        # Cargar el caché
        cache_file = os.path.join(os.path.dirname(__file__), '..', 'edition_cache.json')
        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        
        fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
        
        # Buscar la referencia más cercana ANTERIOR a la fecha solicitada
        mejor_ref = None
        fecha_ref_mas_cercana = None
        
        for fecha_cache, edicion_cache in cache.items():
            fecha_cache_obj = datetime.strptime(fecha_cache, "%d-%m-%Y")
            
            # Solo considerar fechas anteriores o iguales
            if fecha_cache_obj <= fecha_obj:
                if mejor_ref is None or fecha_cache_obj > fecha_ref_mas_cercana:
                    fecha_ref_mas_cercana = fecha_cache_obj
                    mejor_ref = (fecha_cache, int(edicion_cache))
        
        if mejor_ref:
            fecha_ref, edicion_ref = mejor_ref
            fecha_ref_obj = datetime.strptime(fecha_ref, "%d-%m-%Y")
            
            # Contar días hábiles entre las dos fechas
            dias_habiles = 0
            fecha_actual = fecha_ref_obj + timedelta(days=1)
            
            while fecha_actual <= fecha_obj:
                # Si es lunes a viernes (0-4), es día hábil
                if fecha_actual.weekday() < 5:
                    dias_habiles += 1
                fecha_actual += timedelta(days=1)
            
            # Calcular la edición estimada
            edicion_estimada = edicion_ref + dias_habiles
            
            print(f"[EDITION] Estimación:")
            print(f"  - Referencia: {fecha_ref} (edición {edicion_ref})")
            print(f"  - Objetivo: {fecha}")
            print(f"  - Días hábiles: {dias_habiles}")
            print(f"  - Edición estimada: {edicion_estimada}")
            
            # Validar que no exista ya esa edición en otra fecha
            for f, e in cache.items():
                if int(e) == edicion_estimada and f != fecha:
                    print(f"[ALERTA] Edición {edicion_estimada} duplicada con {f}")
                    # Incrementar hasta encontrar una edición libre
                    ediciones_usadas = set(int(e) for e in cache.values())
                    while edicion_estimada in ediciones_usadas:
                        edicion_estimada += 1
                    print(f"[ALERTA] Nueva edición asignada: {edicion_estimada}")
                    break
            
            # Actualizar el caché con la nueva estimación
            cache[fecha] = str(edicion_estimada)
            cache_ordenado = dict(sorted(cache.items(), 
                                       key=lambda x: datetime.strptime(x[0], "%d-%m-%Y")))
            
            with open(cache_file, 'w') as f:
                json.dump(cache_ordenado, f, indent=2)
            
            print(f"[EDITION] Caché actualizado: {fecha} -> {edicion_estimada}")
            return str(edicion_estimada)
            
    except Exception as e:
        print(f"[EDITION] Error en estimación: {e}")
    
    # Valor por defecto basado en fecha más reciente conocida
    print("[EDITION] Usando estimación por defecto")
    return None

def extraer_avisos_destacados(soup):
    """Extrae avisos destacados del HTML del Diario Oficial."""
    avisos = []
    seccion_actual = None
    for tag in soup.find_all(['b', 'strong', 'h3', 'h2', 'h1', 'td', 'th']):
        texto = tag.get_text(strip=True).upper()
        if 'AVISOS DESTACADOS' in texto:
            seccion_actual = 'AVISOS DESTACADOS'
        elif seccion_actual == 'AVISOS DESTACADOS':
            for link in tag.find_all_next("a", href=True):
                href = link["href"]
                if href.endswith(".pdf"):
                    parent = link.find_parent("tr") or link.find_parent("li") or link.parent
                    titulo = None
                    if parent:
                        titulo = parent.get_text(" ", strip=True)
                        titulo = re.sub(r"Ver PDF.*", "", titulo).strip()
                    if not titulo:
                        titulo = "(Sin título)"
                    print(f"[AVISO DESTACADO] Título: {titulo} | PDF: {href}")
                    avisos.append({
                        "seccion": seccion_actual,
                        "titulo": titulo,
                        "url_pdf": href,
                        "relevante": False,
                        "resumen": ""
                    })
                siguiente_texto = link.find_next(string=True)
                if siguiente_texto and 'NORMAS' in siguiente_texto.strip().upper():
                    seccion_actual = None
                    break
    return avisos

def extraer_avisos_destacados_tabla(soup):
    """Extrae avisos destacados y licitaciones públicas desde filas <tr class='content'> en la tabla principal."""
    avisos = []
    for tr in soup.find_all('tr', class_='content'):
        tds = tr.find_all('td')
        if len(tds) >= 2:
            texto = tds[0].get_text(strip=True)
            link_tag = tds[1].find('a', href=True)
            if link_tag:
                href = link_tag['href']
                if es_licitacion_publica(texto):
                    print(f"[AVISO LICITACIÓN] Título: {texto} | PDF: {href}")
                    avisos.append({
                        "seccion": "AVISOS DESTACADOS",
                        "titulo": texto,
                        "url_pdf": href,
                        "relevante": True,
                        "resumen": ""
                    })
    return avisos

def obtener_sumario_diario_oficial(fecha=None, force_refresh=False):
    """
    Scrapea el sumario del Diario Oficial para la fecha dada (formato dd-mm-aaaa).
    Retorna una lista de dicts con título, enlace al PDF, relevancia y resumen.
    SIEMPRE incluye llamados a licitación pública.
    Además, retorna los valores del dólar y euro si están disponibles.
    """
    from datetime import datetime as dt
    
    # Inicializar variables por defecto
    html = None
    resultado_default = {"publicaciones": [], "valores_monedas": None, "total_documentos": 0}
    
    try:
        if fecha is None:
            fecha = datetime.now().strftime("%d-%m-%Y")
        fecha_cache = dt.strptime(fecha, "%d-%m-%Y")
        # --- CACHÉ RESULTADO FINAL ---
        if not force_refresh:
            resultado_cache = cache_service.get_scraping_result(fecha_cache)
            if resultado_cache and isinstance(resultado_cache, dict) and 'publicaciones' in resultado_cache:
                # print(f"[CACHE] Usando resultado final del scraping desde caché para {fecha}")
                return resultado_cache
        # --- CACHÉ HTML POR FECHA ---
        # Primero intentar obtener el número de edición
        edition = obtener_numero_edicion(fecha)
        if not edition:
            print(f"[INFO] No se pudo obtener número de edición para {fecha}, usando valor vacío")
            edition = ""
        else:
            print(f"[INFO] Número de edición obtenido: {edition}")
        
        url = f"{BASE_URL}?date={fecha}&edition={edition}&v=1"
        # Descargar HTML principal
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        sumario = []
        vistos = set()
        seccion_actual = None
        valores_monedas = None
        total_documentos = 0
        no_relevantes = []
        # Primero, procesar TODAS las publicaciones en tr.content
        todas_las_publicaciones = []
        for tr in soup.find_all('tr', class_='content'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                titulo = tds[0].get_text(strip=True)
                titulo = re.sub(r"Ver PDF.*", "", titulo).strip()
                titulo = titulo.replace(' <span class="border dotted"></span>', '').strip()
                
                link_tag = tds[1].find('a', href=True)
                if link_tag and link_tag['href'].endswith('.pdf'):
                    href = link_tag['href']
                    clave = (titulo, href)
                    if clave not in vistos:
                        vistos.add(clave)
                        total_documentos += 1
                        
                        # Evaluar relevancia con IA
                        es_relevante, razon = evaluador_relevancia.evaluar_relevancia(titulo)
                        es_lic = es_licitacion_publica(titulo)
                        
                        # Buscar sección actual
                        seccion_encontrada = None
                        tr_parent = tr.find_parent('table')
                        if tr_parent:
                            # Buscar hacia atrás en la tabla para encontrar la sección
                            for prev in tr_parent.find_all_previous(['td', 'th']):
                                texto_prev = prev.get_text(strip=True).upper()
                                if texto_prev in [s.upper() for s in SECCIONES_VALIDAS]:
                                    seccion_encontrada = texto_prev
                                    break
                        
                        if not seccion_encontrada:
                            seccion_encontrada = "NORMAS GENERALES"  # Default
                        
                        todas_las_publicaciones.append({
                            "seccion": seccion_encontrada,
                            "titulo": titulo,
                            "url_pdf": href,
                            "relevante": es_relevante,
                            "es_licitacion": es_lic,
                            "razon_relevancia": razon,
                            "resumen": "",
                            "es_sii": es_contenido_sii(titulo)
                        })
        
        # Procesar certificado de monedas
        for pub in todas_las_publicaciones:
            if "TIPOS DE CAMBIO" in pub['titulo'].upper() and "PARIDADES DE MONEDAS EXTRANJERAS" in pub['titulo'].upper():
                texto_pdf = extraer_texto_pdf_mixto(pub['url_pdf'])
                valores_monedas = extraer_valores_dolar_euro(texto_pdf)
                break
        
        # Inicializar listas antes de procesar avisos destacados
        publicaciones_relevantes = []
        no_relevantes = []
        licitaciones = []
        # --- EXTRAER NORMAS PARTICULARES ---
        if edition:
            url_normas_part = f"https://www.diariooficial.interior.gob.cl/edicionelectronica/normas_particulares.php?date={fecha}&edition={edition}"
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                resp_normas = requests.get(url_normas_part, headers=headers, timeout=30)
                resp_normas.raise_for_status()
                soup_normas = BeautifulSoup(resp_normas.text, "html.parser")
                
                print(f"[INFO] Procesando página de normas particulares")
                
                # Buscar todas las filas con contenido
                normas_part_encontradas = 0
                
                for tr in soup_normas.find_all('tr', class_='content'):
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        titulo = tds[0].get_text(strip=True)
                        titulo = re.sub(r"Ver PDF.*", "", titulo).strip()
                        titulo = titulo.replace(' <span class="border dotted"></span>', '').strip()
                        
                        link_tag = tds[1].find('a', href=True)
                        if link_tag and link_tag['href'].endswith('.pdf'):
                            href = link_tag['href']
                            clave = (titulo, href)
                            if clave not in vistos:
                                vistos.add(clave)
                                normas_part_encontradas += 1
                                total_documentos += 1  # Contar en el total
                                
                                # Evaluar relevancia con IA
                                es_relevante, razon = evaluador_relevancia.evaluar_relevancia(titulo)
                                es_lic = es_licitacion_publica(titulo)
                                
                                todas_las_publicaciones.append({
                                    "seccion": "NORMAS PARTICULARES",
                                    "titulo": titulo,
                                    "url_pdf": href,
                                    "relevante": es_relevante,
                                    "es_licitacion": es_lic,
                                    "razon_relevancia": razon,
                                    "resumen": "",
                                    "es_sii": es_contenido_sii(titulo)
                                })
                
                print(f"[INFO] Se encontraron {normas_part_encontradas} normas particulares")
                
            except Exception as e:
                print(f"[WARNING] No se pudo extraer normas particulares: {e}")
        
        # Extraer avisos destacados de otras fuentes
        # --- EXTRAER AVISOS DESTACADOS DE LA PÁGINA DEDICADA ---
        if edition:
            # La URL correcta incluye /edicionelectronica/
            url_avisos = f"https://www.diariooficial.interior.gob.cl/edicionelectronica/avisos_destacados.php?date={fecha}&edition={edition}"
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                resp_avisos = requests.get(url_avisos, headers=headers, timeout=30)
                resp_avisos.raise_for_status()
                soup_avisos = BeautifulSoup(resp_avisos.text, "html.parser")
                
                print(f"[INFO] Procesando página de avisos destacados")
                
                # Buscar todas las filas con contenido
                filas_avisos = soup_avisos.find_all('tr')
                avisos_encontrados = 0
                
                for fila in filas_avisos:
                    texto_fila = fila.get_text(strip=True)
                    enlaces = fila.find_all('a', href=True)
                    
                    for enlace in enlaces:
                        if enlace['href'].endswith('.pdf'):
                            # Extraer título (texto antes del enlace)
                            titulo = texto_fila.replace('Ver PDF', '').replace(enlace.get_text(), '').strip()
                            titulo = re.sub(r'\(CVE-\d+\).*', '', titulo).strip()
                            
                            if titulo:
                                url_pdf = enlace['href']
                                clave = (titulo, url_pdf)
                                
                                if clave not in vistos:
                                    vistos.add(clave)
                                    avisos_encontrados += 1
                                    total_documentos += 1  # Contar avisos destacados en el total
                                    
                                    # Evaluar relevancia
                                    es_relevante, razon = evaluador_relevancia.evaluar_relevancia(titulo)
                                    es_lic = es_licitacion_publica(titulo)
                                    
                                    if es_relevante:
                                        todas_las_publicaciones.append({
                                            "seccion": "AVISOS DESTACADOS",
                                            "titulo": titulo,
                                            "url_pdf": url_pdf,
                                            "relevante": es_relevante,
                                            "es_licitacion": es_lic,
                                            "razon_relevancia": razon,
                                            "resumen": "",
                                            "es_sii": es_contenido_sii(titulo)
                                        })
                                        
                                        if es_lic:
                                            print(f"[LICITACIÓN EN AVISOS] {titulo}")
                                        else:
                                            print(f"[AVISO RELEVANTE] {titulo}")
                
                print(f"[INFO] Se encontraron {avisos_encontrados} avisos destacados")
                
            except Exception as e:
                print(f"[WARNING] No se pudo extraer avisos destacados: {e}")
        
        # Ahora separar todas las publicaciones (incluyendo avisos destacados)
        publicaciones_relevantes = [p for p in todas_las_publicaciones if p['relevante']]
        no_relevantes = [p for p in todas_las_publicaciones if not p['relevante']]
        licitaciones = [p for p in publicaciones_relevantes if p.get('es_licitacion', False)]
        
        # Procesar todas las publicaciones relevantes
        sumario = []
        for pub in publicaciones_relevantes:
            texto_pdf = extraer_texto_pdf_mixto(pub['url_pdf'])
            
            # Re-evaluar relevancia con el contenido del PDF para mayor precisión
            if texto_pdf and len(texto_pdf) > 100:
                es_relevante_final, razon_final = evaluador_relevancia.evaluar_relevancia(pub['titulo'], texto_pdf)
                if not es_relevante_final:
                    print(f"[DESCARTADA] {pub['titulo']} - {razon_final}")
                    continue
            
            pub['resumen'] = generar_resumen_desde_texto(texto_pdf, pub['titulo'])
            sumario.append(pub)
            
            # Log de publicaciones incluidas
            tipo = "LICITACIÓN" if pub.get('es_licitacion', False) else "RELEVANTE"
            print(f"[{tipo}] {pub['titulo']}")
            print(f"  Razón: {pub.get('razon_relevancia', 'Cumple criterios')}")
        
        # 3. Si no hay ninguna publicación (ni licitaciones ni relevantes), incluir al menos una
        if not sumario and no_relevantes:
            # Buscar la publicación más importante entre las no relevantes
            PALABRAS_CLAVE_IMPORTANTES = [
                "decreto supremo", "ley", "reforma", "tipos de cambio", "fija", 
                "establece", "aprueba", "reglamento"
            ]
            
            mejor_candidata = None
            mejor_puntaje = 0
            
            for pub in no_relevantes[:10]:  # Revisar solo las primeras 10
                titulo_lower = pub["titulo"].lower()
                puntaje = sum(2 if palabra in titulo_lower else 0 for palabra in PALABRAS_CLAVE_IMPORTANTES)
                if puntaje > mejor_puntaje:
                    mejor_puntaje = puntaje
                    mejor_candidata = pub
            
            # Si encontramos alguna candidata razonable, incluirla
            if mejor_candidata:
                texto_pdf = extraer_texto_pdf_mixto(mejor_candidata['url_pdf'])
                mejor_candidata['resumen'] = generar_resumen_desde_texto(texto_pdf, mejor_candidata['titulo'])
                sumario.append(mejor_candidata)
                print(f"[ÚNICA PUBLICACIÓN] {mejor_candidata['titulo']}")
        
        print(f"\n[RESUMEN FINAL] Total documentos: {total_documentos}")
        print(f"[RESUMEN FINAL] Licitaciones incluidas: {len(licitaciones)}")
        print(f"[RESUMEN FINAL] Publicaciones en informe: {len(sumario)}")
        
        resultado = {"publicaciones": sumario, "valores_monedas": valores_monedas, "total_documentos": total_documentos}
        cache_service.set_scraping_result(fecha_cache, resultado)
        return resultado
    except Exception as e:
        pass  # Enviar alerta solo a soporte interno, nunca a clientes
        send_mail(
            subject='[ALERTA] Error general en scraping Diario Oficial',
            message=f'No se pudo procesar la edición del Diario Oficial para la fecha {fecha}.\nError: {str(e)}',
            from_email="contacto@informediariochile.cl",
            recipient_list=['soporte@informediario.cl'],  # SOLO INTERNO
            fail_silently=True
        )
        return {"publicaciones": [], "valores_monedas": None, "total_documentos": 0} 