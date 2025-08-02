"""
Scraper específico para obtener novedades tributarias del Servicio de Impuestos Internos
desde su sitio oficial https://www.sii.cl/

Este módulo contiene las funciones para extraer:
- Circulares
- Resoluciones Exentas
- Jurisprudencia Administrativa (pendiente de implementación con Selenium)
"""

# ==================== IMPORTACIONES ====================
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
import json
import time
from dotenv import load_dotenv

# Configurar Django si no está configurado
try:
    import django
    from django.conf import settings
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
        django.setup()
    from alerts.services.cache_service import cache_service
    from alerts.utils.rate_limiter import rate_limited
    from alerts.utils.retry_utils import retry
except ImportError:
    # Fallback si Django no está disponible
    def rate_limited(func):
        def wrapper(*args, **kwargs):
            time.sleep(1)  # Simple rate limiting
            return func(*args, **kwargs)
        return wrapper
    
    def retry(max_retries=3, backoff_factor=2):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for i in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if i == max_retries - 1:
                            raise
                        time.sleep(backoff_factor ** i)
                return func(*args, **kwargs)
            return wrapper
        return decorator

# ==================== CONSTANTES ====================
BASE_URL_SII = "https://www.sii.cl"

# Mapeo de meses en español a números
MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

# ==================== FUNCIONES AUXILIARES ====================

def convertir_fecha_sii_a_datetime(fecha_str):
    """
    Convierte fecha del formato 'dd de Mes de YYYY' a datetime
    
    Args:
        fecha_str (str): Fecha en formato 'dd de Mes de YYYY'
    
    Returns:
        datetime: Objeto datetime o None si no se puede convertir
    """
    try:
        # Ejemplo: "18 de Julio de 2025"
        fecha_str = fecha_str.lower().strip()
        partes = fecha_str.split(' de ')
        
        if len(partes) != 3:
            return None
            
        dia = int(partes[0])
        mes_str = partes[1]
        anio = int(partes[2])
        
        mes = MESES_ES.get(mes_str)
        if not mes:
            return None
            
        return datetime(anio, mes, dia)
    except (ValueError, IndexError):
        return None

def es_fecha_del_dia_anterior(fecha_str, fecha_referencia):
    """
    Verifica si una fecha corresponde al día anterior a la fecha de referencia
    
    Args:
        fecha_str (str): Fecha en formato 'dd de Mes de YYYY'
        fecha_referencia (datetime): Fecha de referencia
    
    Returns:
        bool: True si es del día anterior
    """
    fecha_doc = convertir_fecha_sii_a_datetime(fecha_str)
    if not fecha_doc:
        return False
    
    dia_anterior = fecha_referencia - timedelta(days=1)
    return fecha_doc.date() == dia_anterior.date()

def mejorar_descripcion_tributaria(descripcion, tipo_documento):
    """
    Mejora las descripciones tributarias para que sean más claras y comprensibles
    """
    if not descripcion or not isinstance(descripcion, str):
        return None
    
    # Patrones de mejora específicos para contenido tributario
    mejoras = {
        # Términos técnicos -> Explicaciones más claras
        'tabla de cálculos de reajustes y multas': 'actualización de tasas de reajuste e intereses por pagos tardíos de impuestos',
        'tablas de impuesto único de segunda categoría': 'actualización de tramos y tasas del impuesto a los trabajadores dependientes',
        'operaciones de crédito de dinero': 'actualización del valor de la Unidad de Fomento para cálculos crediticios',
        'delega en los': 'transfiere facultades administrativas a',
        'reorganiza las unidades': 'reestructura la organización interna de',
        'ajusta nómina': 'actualiza la lista de contribuyentes',
        'declara término de giro': 'oficializa el cierre de actividades comerciales',
        'modifica resolución': 'actualiza disposiciones anteriores',
        'imparte instrucciones': 'establece nuevas directrices',
        'establece procedimiento': 'define el proceso para'
    }
    
    descripcion_mejorada = descripcion.lower()
    
    # Aplicar mejoras
    for tecnico, claro in mejoras.items():
        if tecnico in descripcion_mejorada:
            descripcion_mejorada = descripcion_mejorada.replace(tecnico, claro)
    
    # Capitalizar primera letra
    if descripcion_mejorada:
        descripcion_mejorada = descripcion_mejorada[0].upper() + descripcion_mejorada[1:]
    
    # Si la descripción sigue siendo muy técnica o vacía, generar una más clara
    if not descripcion_mejorada or len(descripcion_mejorada.strip()) < 20:
        if tipo_documento == 'circular':
            return f"Circular del SII que informa sobre procedimientos tributarios específicos"
        elif tipo_documento == 'resolucion':
            return f"Resolución del SII que establece nuevas disposiciones administrativas"
        else:
            return f"Documento del SII que regula materias tributarias específicas"
    
    # Permitir descripciones más completas, limitando solo si son excesivamente largas
    if len(descripcion_mejorada) > 300:
        # Truncar en el último punto o coma para mantener frases completas
        for i in range(299, 200, -1):
            if descripcion_mejorada[i] in '.,:':
                descripcion_mejorada = descripcion_mejorada[:i+1]
                break
        else:
            # Si no hay puntuación, truncar en espacio
            ultimo_espacio = descripcion_mejorada.rfind(' ', 200, 299)
            if ultimo_espacio > 200:
                descripcion_mejorada = descripcion_mejorada[:ultimo_espacio] + "..."
            else:
                descripcion_mejorada = descripcion_mejorada[:297] + "..."
    
    return descripcion_mejorada

# ==================== FUNCIONES DE SCRAPING ====================

@rate_limited
@retry(max_retries=3, backoff_factor=2)
def obtener_circulares_sii(year=None):
    """
    Obtiene las circulares del SII para un año específico
    
    Args:
        year (int): Año a consultar. Si no se especifica, usa el año actual.
    
    Returns:
        list: Lista de diccionarios con información de circulares
    """
    if year is None:
        year = datetime.now().year
    
    # Intentar múltiples URLs posibles del SII
    urls_posibles = [
        f"{BASE_URL_SII}/normativa_legislacion/circulares/circulares_{year}.html",
        f"{BASE_URL_SII}/normativa_legislacion/circulares/circulares.html",
        f"{BASE_URL_SII}/normativa_legislacion/circulares/{year}/indcir{year}.htm",
        f"{BASE_URL_SII}/normativa_legislacion/index_normativa_legislacion.html"
    ]
    
    for url in urls_posibles:
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 404:
                continue  # Probar siguiente URL
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            circulares = []
            
            # Buscar estructura de circulares en el HTML
            # La estructura es: ##### [Circular N° XX del DD de Mes del YYYY](archivo.pdf)
            #                  Descripción de la circular
            #                  _Fuente: Subdirección._
            
            # Buscar todas las secciones h5 que contienen circulares
            for h5 in soup.find_all(['h5', 'h4', 'h3']):
                if 'circular' in h5.get_text().lower():
                    link = h5.find('a', href=True)
                    if link and 'circu' in link['href'] and link['href'].endswith('.pdf'):
                        href = link['href']
                        
                        # Extraer información del título del enlace
                        titulo_enlace = link.get_text(strip=True)
                        
                        # Extraer número de circular
                        match_numero = re.search(r'Circular\s*N[°º]?\s*(\d+)', titulo_enlace, re.IGNORECASE)
                        numero = match_numero.group(1) if match_numero else "N/A"
                        
                        # Extraer fecha
                        match_fecha = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+del?\s+(\d{4})', titulo_enlace, re.IGNORECASE)
                        fecha = None
                        if match_fecha:
                            dia, mes, anio = match_fecha.groups()
                            fecha = f"{dia} de {mes} de {anio}"
                        
                        # Buscar la descripción en el siguiente elemento
                        descripcion = ""
                        siguiente = h5.find_next_sibling()
                        if siguiente and siguiente.name == 'p':
                            desc_text = siguiente.get_text(strip=True)
                            # Filtrar la fuente si está incluida
                            if 'Fuente:' not in desc_text:
                                descripcion = desc_text
                            else:
                                descripcion = desc_text.split('Fuente:')[0].strip()
                        
                        # Si no hay descripción en el siguiente párrafo, buscar en el contenido completo
                        if not descripcion:
                            parent = h5.parent
                            if parent:
                                texto_completo = parent.get_text()
                                # Buscar patrón: después del enlace hasta "Fuente:"
                                patron = rf'{re.escape(titulo_enlace)}.*?\n(.+?)\n.*?Fuente:'
                                match_desc = re.search(patron, texto_completo, re.DOTALL)
                                if match_desc:
                                    descripcion = match_desc.group(1).strip()
                        
                        # URL completa del PDF
                        if href.startswith('http'):
                            url_pdf = href
                        else:
                            url_pdf = f"{BASE_URL_SII}/normativa_legislacion/circulares/{year}/{href}"
                        
                        # Extraer fuente si está disponible
                        fuente = "Subdirección de Fiscalización"  # Default
                        siguiente_fuente = h5.find_next('em')
                        if siguiente_fuente and 'fuente:' in siguiente_fuente.get_text().lower():
                            fuente_text = siguiente_fuente.get_text(strip=True)
                            fuente = fuente_text.replace('Fuente:', '').strip()
                        
                        # Mejorar la descripción para que sea más clara
                        descripcion_mejorada = mejorar_descripcion_tributaria(descripcion, 'circular')
                        
                        circular = {
                            'tipo': 'Circular',
                            'numero': numero,
                            'fecha': fecha,
                            'titulo': descripcion_mejorada or f"Circular N° {numero}",
                            'url_pdf': url_pdf,
                            'fuente': fuente
                        }
                        
                        circulares.append(circular)
        
            # Ordenar por número (más reciente primero)
            try:
                circulares.sort(key=lambda x: int(x['numero']) if x['numero'].isdigit() else 0, reverse=True)
            except:
                pass
            
            print(f"[SII] Se encontraron {len(circulares)} circulares para {year}")
            return circulares
            
        except Exception as e:
            if url == urls_posibles[-1]:  # Si es la última URL
                print(f"[SII] Error obteniendo circulares: {str(e)}")
                return []
            continue  # Probar siguiente URL
    
    # Si ninguna URL funcionó
    print(f"[SII] No se pudo acceder a ninguna URL de circulares")
    return []

@rate_limited
@retry(max_retries=3, backoff_factor=2)
def obtener_resoluciones_exentas_sii(year=None):
    """
    Obtiene las resoluciones exentas del SII para un año específico
    
    Args:
        year (int): Año a consultar. Si no se especifica, usa el año actual.
    
    Returns:
        list: Lista de diccionarios con información de resoluciones exentas
    """
    if year is None:
        year = datetime.now().year
    
    # Intentar múltiples URLs posibles del SII
    urls_posibles = [
        f"{BASE_URL_SII}/normativa_legislacion/resoluciones/resoluciones_{year}.html",
        f"{BASE_URL_SII}/normativa_legislacion/resoluciones/resoluciones.html",
        f"{BASE_URL_SII}/normativa_legislacion/resoluciones/{year}/res_ind{year}.htm",
        f"{BASE_URL_SII}/normativa_legislacion/index_normativa_legislacion.html"
    ]
    
    for url in urls_posibles:
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 404:
                continue  # Probar siguiente URL
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            resoluciones = []
            
            # Buscar estructura de resoluciones en el HTML
            # La estructura es similar a las circulares:
            # ##### [Resolución Exenta SII N° XX del DD de Mes del YYYY](archivo.pdf)
            #       Descripción de la resolución
            #       _Fuente: Subdirección._
            
            for h5 in soup.find_all(['h5', 'h4', 'h3']):
                if 'resolución exenta sii' in h5.get_text().lower():
                    link = h5.find('a', href=True)
                    if link and 'reso' in link['href'] and link['href'].endswith('.pdf'):
                        href = link['href']
                        
                        # Extraer información del título del enlace
                        titulo_enlace = link.get_text(strip=True)
                        
                        # Extraer número de resolución
                        match_numero = re.search(r'Resolución\s*Exenta\s*SII\s*N[°º]?\s*(\d+)', titulo_enlace, re.IGNORECASE)
                        numero = match_numero.group(1) if match_numero else "N/A"
                        
                        # Extraer fecha
                        match_fecha = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+del?\s+(\d{4})', titulo_enlace, re.IGNORECASE)
                        fecha = None
                        if match_fecha:
                            dia, mes, anio = match_fecha.groups()
                            fecha = f"{dia} de {mes} de {anio}"
                        
                        # Buscar la descripción en el siguiente elemento
                        descripcion = ""
                        siguiente = h5.find_next_sibling()
                        if siguiente and siguiente.name == 'p':
                            desc_text = siguiente.get_text(strip=True)
                            # Filtrar la fuente si está incluida
                            if 'Fuente:' not in desc_text:
                                descripcion = desc_text
                            else:
                                descripcion = desc_text.split('Fuente:')[0].strip()
                        
                        # Si no hay descripción en el siguiente párrafo, buscar en el contenido completo
                        if not descripcion:
                            parent = h5.parent
                            if parent:
                                texto_completo = parent.get_text()
                                # Buscar patrón: después del enlace hasta "Fuente:"
                                patron = rf'{re.escape(titulo_enlace)}.*?\n(.+?)\n.*?Fuente:'
                                match_desc = re.search(patron, texto_completo, re.DOTALL)
                                if match_desc:
                                    descripcion = match_desc.group(1).strip()
                        
                        # URL completa del PDF
                        if href.startswith('http'):
                            url_pdf = href
                        else:
                            url_pdf = f"{BASE_URL_SII}/normativa_legislacion/resoluciones/{year}/{href}"
                        
                        # Extraer fuente si está disponible
                        fuente = "Subdirección Jurídica"  # Default
                        siguiente_fuente = h5.find_next('em')
                        if siguiente_fuente and 'fuente:' in siguiente_fuente.get_text().lower():
                            fuente_text = siguiente_fuente.get_text(strip=True)
                            fuente = fuente_text.replace('Fuente:', '').strip()
                        
                        # Mejorar la descripción para que sea más clara
                        descripcion_mejorada = mejorar_descripcion_tributaria(descripcion, 'resolucion')
                        
                        resolucion = {
                            'tipo': 'Resolución Exenta',
                            'numero': numero,
                            'fecha': fecha,
                            'titulo': descripcion_mejorada or f"Resolución Exenta SII N° {numero}",
                            'url_pdf': url_pdf,
                            'fuente': fuente
                        }
                        
                        resoluciones.append(resolucion)
            
            # Ordenar por número (más reciente primero)
            try:
                resoluciones.sort(key=lambda x: int(x['numero']) if x['numero'].isdigit() else 0, reverse=True)
            except:
                pass
            
            print(f"[SII] Se encontraron {len(resoluciones)} resoluciones exentas para {year}")
            return resoluciones
            
        except Exception as e:
            if url == urls_posibles[-1]:  # Si es la última URL
                print(f"[SII] Error obteniendo resoluciones exentas: {str(e)}")
                return []
            continue  # Probar siguiente URL
    
    # Si ninguna URL funcionó
    print(f"[SII] No se pudo acceder a ninguna URL de resoluciones")
    return []

def obtener_jurisprudencia_administrativa_sii(year=None):
    """
    Obtiene jurisprudencia administrativa del SII para un año específico
    Accede directamente a las páginas HTML ya que el API requiere autenticación especial
    
    Args:
        year (int): Año para buscar jurisprudencia
    
    Returns:
        list: Lista de diccionarios con información de jurisprudencia administrativa
    """
    if year is None:
        year = datetime.now().year
    
    # URLs directas de las páginas de jurisprudencia
    urls_jurisprudencia = {
        'IVA': f"{BASE_URL_SII}/normativa_legislacion/jurisprudencia_administrativa/ley_impuesto_ventas/{year}/ley_impuesto_ventas_jadm{year}.htm",
        'Renta': f"{BASE_URL_SII}/normativa_legislacion/jurisprudencia_administrativa/ley_impuesto_renta/{year}/ley_impuesto_renta_jadm{year}.htm",
        'Otras': f"{BASE_URL_SII}/normativa_legislacion/jurisprudencia_administrativa/otras_normas/{year}/otras_normas_jadm{year}.htm"
    }
    
    jurisprudencia = []
    
    # Por ahora retornar lista vacía hasta implementar correctamente el scraping
    # El sitio del SII requiere JavaScript para cargar el contenido dinámicamente
    print(f"[SII] Jurisprudencia administrativa temporalmente no disponible (requiere implementación con Selenium)")
    return jurisprudencia

def obtener_jurisprudencia_sii_reciente(dias=7):
    """
    Wrapper para mantener compatibilidad - llama a obtener_jurisprudencia_administrativa_sii
    """
    return obtener_jurisprudencia_administrativa_sii()

# ==================== FUNCIÓN PRINCIPAL ====================

def obtener_novedades_tributarias_sii(fecha_referencia=None, dias_atras=7):
    """
    Función principal que obtiene todas las novedades tributarias del SII
    para una fecha específica o los últimos días especificados
    
    Args:
        fecha_referencia (str or datetime): Fecha específica para filtrar documentos recientes
                                           Si es string, debe estar en formato 'DD-MM-YYYY'
        dias_atras (int): Número de días hacia atrás para considerar como "reciente"
    
    Returns:
        dict: Diccionario con todas las novedades organizadas por tipo
    """
    # Resultado por defecto en caso de error
    resultado_vacio = {
        'circulares': [],
        'resoluciones_exentas': [],
        'jurisprudencia_administrativa': [],
        'total_novedades': 0
    }
    
    try:
        year = datetime.now().year
        
        # Convertir string a datetime si es necesario
        if fecha_referencia and isinstance(fecha_referencia, str):
            fecha_referencia = datetime.strptime(fecha_referencia, "%d-%m-%Y")
        
        # Obtener circulares
        circulares = obtener_circulares_sii(year)
        
        # Obtener resoluciones exentas
        resoluciones = obtener_resoluciones_exentas_sii(year)
        
        # Obtener jurisprudencia administrativa
        jurisprudencia = obtener_jurisprudencia_administrativa_sii(year)
        
        # Función auxiliar para verificar si un documento es reciente
        def es_documento_reciente(fecha_str, fecha_ref, dias):
            """Verifica si un documento es de los últimos 'dias' días"""
            fecha_doc = convertir_fecha_sii_a_datetime(fecha_str)
            if not fecha_doc:
                return False
            
            fecha_limite = fecha_ref - timedelta(days=dias)
            return fecha_doc >= fecha_limite and fecha_doc <= fecha_ref
        
        # Filtrar según criterio de fecha
        if fecha_referencia:
            print(f"[SII] Obteniendo novedades tributarias recientes hasta el {fecha_referencia.strftime('%d-%m-%Y')}...")
            
            # Filtrar documentos de los últimos días
            circulares_recientes = []
            for circular in circulares:
                if circular.get('fecha') and es_documento_reciente(circular['fecha'], fecha_referencia, dias_atras):
                    circulares_recientes.append(circular)
            
            resoluciones_recientes = []
            for resolucion in resoluciones:
                if resolucion.get('fecha') and es_documento_reciente(resolucion['fecha'], fecha_referencia, dias_atras):
                    resoluciones_recientes.append(resolucion)
            
            jurisprudencia_reciente = []
            for juris in jurisprudencia:
                if juris.get('fecha') and es_documento_reciente(juris['fecha'], fecha_referencia, dias_atras):
                    jurisprudencia_reciente.append(juris)
            
            # Si no hay documentos recientes, mostrar los más recientes disponibles
            if not circulares_recientes and circulares:
                print(f"[SII] No hay circulares de los últimos {dias_atras} días, mostrando las 3 más recientes")
                circulares_recientes = circulares[:3]
            
            if not resoluciones_recientes and resoluciones:
                print(f"[SII] No hay resoluciones de los últimos {dias_atras} días, mostrando las 3 más recientes")
                resoluciones_recientes = resoluciones[:3]
                
        else:
            print(f"[SII] Obteniendo novedades tributarias más recientes...")
            # Comportamiento por defecto: mostrar las más recientes
            circulares_recientes = circulares[:5]  # Top 5 más recientes
            resoluciones_recientes = resoluciones[:5]  # Top 5 más recientes
            jurisprudencia_reciente = jurisprudencia[:10]  # Top 10 más recientes
        
        resultado = {
            'circulares': circulares_recientes,
            'resoluciones_exentas': resoluciones_recientes,
            'jurisprudencia_administrativa': jurisprudencia_reciente,
            'total_novedades': len(circulares_recientes) + len(resoluciones_recientes) + len(jurisprudencia_reciente)
        }
        
        print(f"[SII] Resumen de novedades:")
        print(f"  - Circulares: {len(circulares_recientes)}")
        print(f"  - Resoluciones Exentas: {len(resoluciones_recientes)}")
        print(f"  - Jurisprudencia Administrativa: {len(jurisprudencia_reciente)}")
        print(f"  - Total: {resultado['total_novedades']}")
        
        return resultado
    
    except Exception as e:
        print(f"[SII] Error general obteniendo novedades tributarias: {str(e)}")
        return resultado_vacio

if __name__ == "__main__":
    try:
        # Test del scraper
        novedades = obtener_novedades_tributarias_sii()
        
        print("\n=== CIRCULARES ===")
        for circular in novedades['circulares']:
            print(f"Circular N° {circular['numero']} - {circular['fecha']}")
            print(f"  {circular['titulo']}")
            print(f"  PDF: {circular['url_pdf']}")
            print()
        
        print("\n=== RESOLUCIONES EXENTAS ===")
        for resolucion in novedades['resoluciones_exentas']:
            print(f"Resolución Exenta SII N° {resolucion['numero']} - {resolucion['fecha']}")
            print(f"  {resolucion['titulo']}")
            print(f"  PDF: {resolucion['url_pdf']}")
            print()
    except Exception as e:
        print(f"[SII] Error ejecutando scraper de prueba: {str(e)}")