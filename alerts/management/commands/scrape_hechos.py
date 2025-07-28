"""
Comando para scrapear hechos esenciales del sitio web de la CMF
Incluye criterios profesionales de clasificación basados en Bloomberg/Refinitiv
"""
import os
import re
import time
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from alerts.models import Empresa, HechoEsencial
from alerts.cmf_criterios_profesionales import calcular_relevancia_profesional, EMPRESAS_IPSA
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
import requests
from bs4 import BeautifulSoup
import PyPDF2
from io import BytesIO
import openai
from dotenv import load_dotenv
import json

# Importar servicios robustos existentes
from alerts.services.cache_service import cache_service
from alerts.services.pdf_extractor import PDFExtractor
from alerts.utils.rate_limiter import rate_limited
from alerts.utils.retry_utils import retry

load_dotenv()

class Command(BaseCommand):
    help = 'Scrapea los hechos esenciales del sitio web de la CMF con criterios profesionales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=1,
            help='Número de días hacia atrás para buscar hechos esenciales'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Modo debug con más información'
        )

    def __init__(self):
        super().__init__()
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        self.debug_mode = False
        self.pdf_extractor = PDFExtractor()

    def handle(self, *args, **options):
        self.debug_mode = options.get('debug', False)
        dias = options['dias']
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'INICIANDO SCRAPING DE HECHOS ESENCIALES CMF'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}\n'))
        
        # Configurar el driver
        driver = self.setup_driver()
        
        try:
            # Obtener hechos esenciales
            hechos = self.scrape_hechos_esenciales(driver, dias)
            
            if hechos:
                self.stdout.write(self.style.SUCCESS(f'\nEncontrados {len(hechos)} hechos esenciales'))
                self.procesar_hechos(hechos)
            else:
                self.stdout.write(self.style.WARNING('No se encontraron hechos esenciales nuevos'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error en el proceso: {str(e)}'))
            if self.debug_mode:
                import traceback
                traceback.print_exc()
        finally:
            driver.quit()
            
        self.stdout.write(self.style.SUCCESS('\nProceso completado'))

    def setup_driver(self):
        """Configura el driver de Selenium con undetected-chromedriver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        if not self.debug_mode:
            options.add_argument('--headless')
            
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        return driver

    def scrape_hechos_esenciales(self, driver, dias):
        """Scrapea los hechos esenciales de los últimos N días"""
        hechos = []
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        url = "https://www.cmfchile.cl/institucional/hechos/hechos_portada.php"
        
        self.stdout.write(f'Accediendo a {url}')
        driver.get(url)
        
        # Esperar a que la página cargue
        time.sleep(5)
        
        try:
            # Buscar la tabla de hechos esenciales
            tabla = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "lista_registros"))
            )
            
            # Obtener todas las filas
            filas = tabla.find_elements(By.TAG_NAME, "tr")
            
            if self.debug_mode:
                self.stdout.write(f'Encontradas {len(filas)} filas en la tabla')
            
            for fila in filas:
                try:
                    columnas = fila.find_elements(By.TAG_NAME, "td")
                    if len(columnas) >= 3:
                        # Extraer datos según la estructura actual de CMF
                        fecha_str = columnas[0].text.strip()
                        
                        # El enlace y título están en la segunda columna
                        enlace_elem = columnas[1].find_element(By.TAG_NAME, "a")
                        titulo = enlace_elem.text.strip()
                        url_pdf = enlace_elem.get_attribute("href")
                        
                        # La empresa está en la tercera columna
                        empresa_nombre = columnas[2].text.strip()
                        
                        # Parsear fecha
                        try:
                            # Formato: DD/MM/YYYY HH:MM:SS
                            fecha = datetime.strptime(fecha_str.split()[0], "%d/%m/%Y")
                            fecha = timezone.make_aware(fecha)
                        except:
                            if self.debug_mode:
                                self.stdout.write(f'Error parseando fecha: {fecha_str}')
                            continue
                            
                        # Verificar si está dentro del rango de fechas
                        if fecha < fecha_limite:
                            if self.debug_mode:
                                self.stdout.write(f'Fecha {fecha} fuera de rango, deteniendo búsqueda')
                            break
                            
                        # Agregar a la lista
                        hechos.append({
                            'fecha': fecha,
                            'empresa': empresa_nombre,
                            'titulo': titulo,
                            'url': url_pdf
                        })
                        
                        if self.debug_mode:
                            self.stdout.write(f'Hecho encontrado: {empresa_nombre} - {titulo}')
                        
                except Exception as e:
                    if self.debug_mode:
                        self.stdout.write(self.style.WARNING(f'Error procesando fila: {str(e)}'))
                    continue
                    
        except TimeoutException:
            self.stdout.write(self.style.ERROR('Timeout esperando la tabla de hechos esenciales'))
            # Guardar HTML para debug
            if self.debug_mode:
                with open('debug_cmf_scraper.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
            
        return hechos

    @rate_limited
    @retry(max_retries=3, backoff_factor=2)
    def descargar_pdf_con_cache(self, url_pdf):
        """Descarga un PDF usando caché y rate limiting"""
        # Intentar obtener del caché
        content = cache_service.get_pdf_content(url_pdf)
        if content:
            return content
        
        response = requests.get(url_pdf, timeout=30)
        response.raise_for_status()
        
        # Guardar en caché
        cache_service.set_pdf_content(url_pdf, response.content)
        return response.content

    def procesar_hechos(self, hechos):
        """Procesa los hechos esenciales encontrados"""
        nuevos = 0
        actualizados = 0
        errores = 0
        
        for hecho in hechos:
            try:
                with transaction.atomic():
                    # Obtener o crear empresa
                    empresa, created = Empresa.objects.get_or_create(
                        nombre=hecho['empresa'],
                        defaults={
                            'es_ipsa': hecho['empresa'].upper() in [e.upper() for e in EMPRESAS_IPSA]
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'  Nueva empresa creada: {empresa.nombre}')
                    
                    # Verificar si el hecho ya existe
                    hecho_obj, created = HechoEsencial.objects.get_or_create(
                        url=hecho['url'],
                        defaults={
                            'empresa': empresa,
                            'titulo': hecho['titulo'],
                            'fecha_publicacion': hecho['fecha'],
                            'es_empresa_ipsa': empresa.es_ipsa
                        }
                    )
                    
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'\nNuevo hecho: {empresa.nombre}'))
                        self.stdout.write(f'  Título: {hecho["titulo"][:80]}...')
                        nuevos += 1
                    else:
                        # Si ya existe pero no tiene resumen o categoría, actualizar
                        if not hecho_obj.resumen or not hecho_obj.categoria or hecho_obj.categoria == 'MODERADO':
                            self.stdout.write(f'\nActualizando hecho existente: {empresa.nombre}')
                            actualizados += 1
                        else:
                            continue
                    
                    # Procesar el PDF y generar resumen si no existe
                    if not hecho_obj.resumen:
                        self.procesar_pdf_hecho(hecho_obj)
                        
                    # Calcular relevancia profesional
                    self.calcular_relevancia_hecho(hecho_obj)
                    
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f'Error procesando hecho: {str(e)}'))
                if self.debug_mode:
                    import traceback
                    traceback.print_exc()
                    
        self.stdout.write(self.style.SUCCESS(f'\nResumen:'))
        self.stdout.write(f'  - Nuevos: {nuevos}')
        self.stdout.write(f'  - Actualizados: {actualizados}')
        self.stdout.write(f'  - Errores: {errores}')

    def procesar_pdf_hecho(self, hecho):
        """Descarga y procesa el PDF del hecho esencial"""
        try:
            # Descargar PDF con caché
            pdf_content = self.descargar_pdf_con_cache(hecho.url)
            
            # Extraer texto del PDF usando el servicio robusto
            texto_completo, metodo = self.pdf_extractor.extract_text(pdf_content, max_pages=5)
            
            if self.debug_mode:
                self.stdout.write(f'  PDF extraído con método: {metodo} ({len(texto_completo)} caracteres)')
            
            # Generar resumen con OpenAI
            if self.openai_api_key and len(texto_completo) > 100:
                resumen = self.generar_resumen_ia(hecho.titulo, texto_completo, hecho.empresa.es_ipsa)
                if resumen:
                    hecho.resumen = resumen
                    hecho.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Resumen generado'))
                else:
                    # Fallback: usar primeras líneas del texto
                    hecho.resumen = texto_completo[:500] + "..."
                    hecho.save()
                    
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ✗ Error procesando PDF: {str(e)}'))

    def generar_resumen_ia(self, titulo, texto, es_ipsa=False):
        """Genera un resumen usando OpenAI con prompts especializados"""
        try:
            # Detectar categoría preliminar para ajustar el prompt
            titulo_lower = titulo.lower()
            es_critico = any(kw in titulo_lower for kw in ['opa', 'fusión', 'quiebra', 'absorción'])
            es_importante = any(kw in titulo_lower for kw in ['gerente general', 'emisión', 'bono', 'directorio'])
            
            # Preparar contexto
            contexto_ipsa = " (Empresa IPSA)" if es_ipsa else ""
            
            if es_critico:
                instrucciones = "Este es un hecho CRÍTICO. Enfócate en el impacto inmediato en el valor de la empresa y las implicaciones para accionistas minoritarios."
            elif es_importante:
                instrucciones = "Este es un hecho IMPORTANTE. Destaca los cambios estructurales y el impacto esperado en la operación."
            else:
                instrucciones = "Resume de manera concisa los puntos clave y el impacto esperado."
            
            prompt = f"""Eres un analista financiero senior especializado en el mercado chileno. Resume el siguiente hecho esencial{contexto_ipsa}.
            
{instrucciones}
            
Título: {titulo}

Contenido: {texto[:4000]}

Genera un resumen profesional en exactamente 3 frases:
1. ¿Qué sucedió? (acción concreta)
2. Datos clave (montos, fechas, porcentajes)
3. Impacto esperado en la empresa/mercado

Usa lenguaje financiero profesional pero claro."""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un analista financiero senior con 20 años de experiencia en el mercado chileno."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error generando resumen con IA: {str(e)}'))
            # Fallback a Gemini si está configurado
            try:
                import google.generativeai as genai
                api_key = os.environ.get('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)
                    return response.text.strip()
            except:
                pass
            return None

    def calcular_relevancia_hecho(self, hecho):
        """Calcula y actualiza la relevancia profesional del hecho"""
        try:
            # Usar la función de criterios profesionales
            relevancia, categoria, es_ipsa = calcular_relevancia_profesional(
                titulo=hecho.titulo,
                materia=hecho.resumen or hecho.titulo,
                entidad=hecho.empresa.nombre,
                contexto=hecho.resumen or ""
            )
            
            # Actualizar el hecho
            hecho.relevancia_profesional = relevancia
            hecho.categoria = categoria
            hecho.es_empresa_ipsa = es_ipsa
            
            # Mapear a relevancia tradicional (1-3)
            if relevancia >= 8:
                hecho.relevancia = 3  # Alta
            elif relevancia >= 5:
                hecho.relevancia = 2  # Media
            else:
                hecho.relevancia = 1  # Baja
                
            hecho.save()
            
            # Emoji según categoría
            emoji_map = {
                'CRITICO': '🔴',
                'IMPORTANTE': '🟡',
                'MODERADO': '🟢',
                'RUTINARIO': '⚪'
            }
            emoji = emoji_map.get(categoria, '')
            
            self.stdout.write(f'  ✓ Relevancia: {emoji} {categoria} ({relevancia:.1f}/10)')
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error calculando relevancia: {str(e)}'))