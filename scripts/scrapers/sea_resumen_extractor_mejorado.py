#!/usr/bin/env python3
"""
Extractor mejorado de resúmenes ejecutivos de proyectos SEA
Versión simplificada que funciona solo con requests
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Optional, Dict
import json

logger = logging.getLogger(__name__)

class SEAResumenExtractorMejorado:
    def __init__(self):
        self.base_url = "https://seia.sea.gob.cl"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'es-419,es;q=0.9,es-ES;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        })
    
    def extraer_resumen_proyecto(self, id_expediente: str) -> Dict[str, str]:
        """
        Extrae el resumen ejecutivo de un proyecto usando su ID
        """
        resultado = {
            'resumen': '',
            'inversion': '',
            'ubicacion': '',
            'titular': '',
            'tipo_proyecto': ''
        }
        
        try:
            # Intentar múltiples endpoints del SEA
            resultado = self._extraer_con_api_interna(id_expediente)
            if resultado.get('resumen'):
                return resultado
            
            # Si falla, intentar con la ficha principal
            resultado = self._extraer_de_ficha_principal(id_expediente)
            if resultado.get('resumen'):
                return resultado
            
            # Intentar con endpoint de búsqueda
            resultado = self._extraer_de_busqueda(id_expediente)
            if resultado.get('resumen'):
                return resultado
                
        except Exception as e:
            logger.error(f"Error extrayendo resumen del proyecto {id_expediente}: {e}")
        
        # NO generar resumen descriptivo aquí - solo retornar datos extraídos
        return resultado
    
    def _extraer_con_api_interna(self, id_expediente: str) -> Dict[str, str]:
        """
        Intenta extraer usando endpoints internos del SEA
        """
        resultado = {
            'resumen': '',
            'inversion': '',
            'ubicacion': '',
            'titular': '',
            'tipo_proyecto': ''
        }
        
        try:
            # Intentar endpoint de API que devuelve JSON
            api_urls = [
                f"{self.base_url}/ws/server/open/getProyecto/{id_expediente}",
                f"{self.base_url}/rest/proyecto/{id_expediente}",
                f"{self.base_url}/api/v1/proyectos/{id_expediente}",
                f"{self.base_url}/expediente/ajax/proyecto_detalle.php?id={id_expediente}"
            ]
            
            for url in api_urls:
                try:
                    response = self.session.get(url, timeout=10, verify=False)
                    if response.status_code == 200:
                        # Intentar parsear como JSON
                        try:
                            data = response.json()
                            # Buscar campos de resumen en el JSON
                            resumen_fields = ['descripcion', 'resumen', 'objetivo', 'descripcion_proyecto', 
                                            'resumen_ejecutivo', 'objeto', 'descripcionProyecto']
                            
                            for field in resumen_fields:
                                if field in data and data[field]:
                                    resultado['resumen'] = str(data[field])[:800]
                                    logger.info(f"✅ Resumen encontrado en API JSON: {field}")
                                    break
                            
                            # Buscar otros campos
                            if 'inversion' in data or 'monto' in data or 'inversionTotal' in data:
                                resultado['inversion'] = str(data.get('inversion', data.get('monto', data.get('inversionTotal', ''))))
                            if 'titular' in data or 'empresa' in data or 'razonSocial' in data:
                                resultado['titular'] = str(data.get('titular', data.get('empresa', data.get('razonSocial', ''))))
                            if 'comuna' in data or 'ubicacion' in data:
                                resultado['ubicacion'] = str(data.get('comuna', data.get('ubicacion', '')))
                            
                            if resultado['resumen']:
                                return resultado
                        except:
                            # No es JSON, continuar
                            pass
                except Exception as e:
                    logger.debug(f"Error con URL {url}: {e}")
                    continue
        except Exception as e:
            logger.debug(f"Error en API interna: {e}")
        
        return resultado
    
    def _extraer_de_ficha_principal(self, id_expediente: str) -> Dict[str, str]:
        """
        Extrae información de la ficha principal del proyecto
        """
        resultado = {
            'resumen': '',
            'inversion': '',
            'ubicacion': '',
            'titular': '',
            'tipo_proyecto': ''
        }
        
        try:
            # URL de la ficha con todos los tabs
            urls = [
                f"{self.base_url}/expediente/ficha/fichaPrincipal.php?modo=ficha&id_expediente={id_expediente}&idExpediente={id_expediente}",
                f"{self.base_url}/expediente/expedientes/mostrar_detalle.php?id_expediente={id_expediente}",
                f"{self.base_url}/expediente/ficha.php?id_expediente={id_expediente}"
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=15, verify=False)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Buscar el resumen en diferentes lugares
                        # 1. Buscar en tablas con headers específicos
                        tablas = soup.find_all('table')
                        for tabla in tablas:
                            filas = tabla.find_all('tr')
                            for fila in filas:
                                celdas = fila.find_all(['td', 'th'])
                                if len(celdas) >= 2:
                                    header = celdas[0].get_text(strip=True).lower()
                                    contenido = celdas[1].get_text(strip=True)
                                    
                                    # Buscar descripción/resumen
                                    if any(palabra in header for palabra in ['descripción', 'descripcion', 'objeto', 'resumen', 'objetivo']):
                                        if len(contenido) > 100 and not resultado['resumen']:
                                            # Limpiar y formatear el resumen
                                            resumen_limpio = ' '.join(contenido.split())
                                            # Tomar solo las primeras oraciones significativas
                                            oraciones = resumen_limpio.split('.')
                                            resumen_final = []
                                            caracteres_total = 0
                                            
                                            for oracion in oraciones:
                                                oracion = oracion.strip()
                                                if oracion and caracteres_total + len(oracion) < 600:
                                                    # Verificar que la oración tiene contenido relevante
                                                    if any(palabra in oracion.lower() for palabra in 
                                                          ['construcción', 'operación', 'instalación', 'proyecto', 
                                                           'consiste', 'contempla', 'comprende', 'incluye', 
                                                           'generación', 'producción', 'extracción', 'planta',
                                                           'parque', 'central', 'línea', 'sistema', 'desarrollo']):
                                                        resumen_final.append(oracion)
                                                        caracteres_total += len(oracion)
                                                        if caracteres_total > 300:  # Suficiente contenido
                                                            break
                                            
                                            if resumen_final:
                                                resultado['resumen'] = '. '.join(resumen_final) + '.'
                                                logger.info(f"✅ Resumen encontrado en tabla: {len(resultado['resumen'])} chars")
                                    
                                    # Buscar inversión
                                    elif any(palabra in header for palabra in ['inversión', 'inversion', 'monto', 'capital']):
                                        if not resultado['inversion'] and contenido:
                                            resultado['inversion'] = contenido
                                    
                                    # Buscar titular
                                    elif any(palabra in header for palabra in ['titular', 'empresa', 'proponente', 'razón social']):
                                        if not resultado['titular'] and contenido:
                                            resultado['titular'] = contenido
                                    
                                    # Buscar ubicación
                                    elif any(palabra in header for palabra in ['comuna', 'ubicación', 'localización', 'región']):
                                        if not resultado['ubicacion'] and contenido:
                                            resultado['ubicacion'] = contenido
                        
                        # 2. Si no encontramos en tablas, buscar en divs con clases específicas
                        if not resultado['resumen']:
                            divs_descripcion = soup.find_all('div', class_=re.compile(r'descripcion|resumen|contenido|detalle', re.I))
                            for div in divs_descripcion:
                                texto = div.get_text(strip=True)
                                if len(texto) > 200 and any(palabra in texto.lower() for palabra in ['proyecto', 'construcción', 'operación']):
                                    # Extraer solo la parte relevante
                                    lineas = texto.split('\n')
                                    resumen_partes = []
                                    for linea in lineas:
                                        linea = linea.strip()
                                        if len(linea) > 50 and not any(skip in linea.lower() for skip in ['menu', 'buscar', 'inicio', 'copyright']):
                                            resumen_partes.append(linea)
                                            if len(' '.join(resumen_partes)) > 400:
                                                break
                                    
                                    if resumen_partes:
                                        resultado['resumen'] = ' '.join(resumen_partes)[:600]
                                        logger.info(f"✅ Resumen encontrado en div: {len(resultado['resumen'])} chars")
                                        break
                        
                        if resultado['resumen']:
                            return resultado
                            
                except Exception as e:
                    logger.debug(f"Error con URL {url}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error en ficha principal: {e}")
        
        return resultado
    
    def _extraer_de_busqueda(self, id_expediente: str) -> Dict[str, str]:
        """
        Busca el proyecto en el buscador del SEA y extrae información
        """
        resultado = {
            'resumen': '',
            'inversion': '',
            'ubicacion': '',
            'titular': '',
            'tipo_proyecto': ''
        }
        
        try:
            # Buscar por ID en el buscador
            search_url = f"{self.base_url}/busqueda/buscarProyecto.php"
            
            # Hacer búsqueda POST
            data = {
                'id_expediente': id_expediente,
                'buscar': '1'
            }
            
            response = self.session.post(search_url, data=data, timeout=10, verify=False)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Buscar resultados de búsqueda
                resultados = soup.find_all('div', class_='resultado_busqueda') or soup.find_all('tr', class_='proyecto')
                
                for resultado_div in resultados:
                    texto = resultado_div.get_text(separator=' ', strip=True)
                    
                    # Extraer información del texto del resultado
                    if 'descripción' in texto.lower() or 'objeto' in texto.lower():
                        # Intentar extraer la descripción
                        import re
                        desc_match = re.search(r'(?:descripción|objeto)[:\s]+(.+?)(?:estado|fecha|$)', texto, re.I)
                        if desc_match:
                            resultado['resumen'] = desc_match.group(1).strip()[:600]
                            logger.info(f"✅ Resumen encontrado en búsqueda")
                            break
                            
        except Exception as e:
            logger.debug(f"Error en búsqueda: {e}")
        
        return resultado
    
    def generar_resumen_descriptivo(self, proyecto: Dict) -> str:
        """
        Genera un resumen descriptivo basado en los datos disponibles del proyecto
        """
        titulo = proyecto.get('titulo', '')
        empresa = proyecto.get('empresa', proyecto.get('titular', ''))
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        tipo = proyecto.get('tipo', 'Proyecto')
        inversion = proyecto.get('inversion', '')
        
        # Analizar el título para extraer información del tipo de proyecto
        titulo_lower = titulo.lower()
        
        descripcion_tipo = ""
        if 'fotovoltaico' in titulo_lower or 'solar' in titulo_lower:
            # Intentar extraer capacidad
            capacidad_match = re.search(r'(\d+[\.,]?\d*)\s*(mw|megawatt|gwh)', titulo_lower, re.I)
            if capacidad_match:
                capacidad = capacidad_match.group(0)
                descripcion_tipo = f"Proyecto de generación de energía solar fotovoltaica con capacidad de {capacidad}"
            else:
                descripcion_tipo = "Proyecto de generación de energía solar fotovoltaica"
        
        elif 'eólico' in titulo_lower or 'aerogenerador' in titulo_lower:
            capacidad_match = re.search(r'(\d+[\.,]?\d*)\s*(mw|megawatt)', titulo_lower, re.I)
            if capacidad_match:
                capacidad = capacidad_match.group(0)
                descripcion_tipo = f"Proyecto de generación de energía eólica con capacidad de {capacidad}"
            else:
                descripcion_tipo = "Proyecto de generación de energía eólica mediante aerogeneradores"
        
        elif 'minero' in titulo_lower or 'mina' in titulo_lower or 'extracción' in titulo_lower:
            if 'áridos' in titulo_lower:
                descripcion_tipo = "Proyecto de extracción y procesamiento de áridos para construcción"
            elif 'cobre' in titulo_lower:
                descripcion_tipo = "Proyecto de extracción y procesamiento de mineral de cobre"
            else:
                descripcion_tipo = "Proyecto de extracción y procesamiento minero"
        
        elif 'inmobiliario' in titulo_lower or 'habitacional' in titulo_lower or 'vivienda' in titulo_lower:
            unidades_match = re.search(r'(\d+)\s*(vivienda|unidad|departamento|casa)', titulo_lower, re.I)
            if unidades_match:
                unidades = unidades_match.group(0)
                descripcion_tipo = f"Proyecto inmobiliario que contempla la construcción de {unidades}"
            else:
                descripcion_tipo = "Proyecto de desarrollo inmobiliario habitacional"
        
        elif 'planta' in titulo_lower:
            if 'tratamiento' in titulo_lower:
                if 'agua' in titulo_lower:
                    descripcion_tipo = "Planta de tratamiento de aguas servidas"
                elif 'residuo' in titulo_lower:
                    descripcion_tipo = "Planta de tratamiento y manejo de residuos"
                else:
                    descripcion_tipo = "Planta de tratamiento industrial"
            elif 'desaladora' in titulo_lower or 'desalinizadora' in titulo_lower:
                descripcion_tipo = "Planta desaladora para producción de agua potable"
            else:
                descripcion_tipo = "Proyecto de instalación de planta industrial"
        
        elif 'línea' in titulo_lower and ('transmisión' in titulo_lower or 'eléctrica' in titulo_lower):
            kv_match = re.search(r'(\d+)\s*kv', titulo_lower, re.I)
            if kv_match:
                kv = kv_match.group(0)
                descripcion_tipo = f"Línea de transmisión eléctrica de {kv}"
            else:
                descripcion_tipo = "Línea de transmisión eléctrica de alta tensión"
        
        elif 'acuícola' in titulo_lower or 'salmón' in titulo_lower or 'cultivo' in titulo_lower:
            descripcion_tipo = "Proyecto de cultivo acuícola para producción de salmónidos"
        
        elif 'puerto' in titulo_lower or 'terminal' in titulo_lower:
            descripcion_tipo = "Proyecto de infraestructura portuaria"
        
        elif 'carretera' in titulo_lower or 'ruta' in titulo_lower or 'camino' in titulo_lower:
            km_match = re.search(r'(\d+[\.,]?\d*)\s*km', titulo_lower, re.I)
            if km_match:
                km = km_match.group(0)
                descripcion_tipo = f"Proyecto vial de {km} de extensión"
            else:
                descripcion_tipo = "Proyecto de infraestructura vial"
        
        else:
            # Descripción genérica basada en el tipo
            descripcion_tipo = f"{tipo} de inversión"
        
        # Construir el resumen completo
        resumen = descripcion_tipo
        
        if empresa:
            resumen += f", presentado por {empresa}"
        
        if region and comuna:
            resumen += f", ubicado en la comuna de {comuna}, {region}"
        elif region:
            resumen += f", ubicado en {region}"
        elif comuna:
            resumen += f", ubicado en {comuna}"
        
        if inversion:
            # Formatear la inversión
            if 'USD' in inversion or 'US$' in inversion or 'MM' in inversion:
                resumen += f". Inversión estimada: {inversion}"
            elif re.search(r'\d', inversion):
                resumen += f". Inversión: {inversion}"
        
        # Agregar información sobre el estado del proceso si está disponible
        estado = proyecto.get('estado', '')
        if estado and estado not in resumen:
            if 'admitido' in estado.lower():
                resumen += ". El proyecto ha sido admitido a tramitación"
            elif 'evaluación' in estado.lower():
                resumen += ". Actualmente en proceso de evaluación ambiental"
        
        return resumen
    
    def obtener_id_de_url(self, url: str) -> Optional[str]:
        """
        Extrae el ID del expediente desde una URL del SEA
        """
        # Buscar patrón id_expediente=XXXXX o idExpediente=XXXXX
        patterns = [
            r'id_expediente=(\d+)',
            r'idExpediente=(\d+)',
            r'id=(\d+)',
            r'/expediente/(\d+)',
            r'/proyecto/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.I)
            if match:
                return match.group(1)
        
        return None


# Instancia global
sea_resumen_extractor_mejorado = SEAResumenExtractorMejorado()


if __name__ == "__main__":
    # Prueba con el proyecto Manquel Solar
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*80)
    print("🔍 PRUEBA DE EXTRACCIÓN DE RESUMEN - PROYECTO MANQUEL SOLAR")
    print("="*80)
    
    extractor = SEAResumenExtractorMejorado()
    
    # URL del proyecto Manquel Solar
    url_manquel = "https://seia.sea.gob.cl/expediente/ficha/fichaPrincipal.php?id_expediente=2159854892&idExpediente=2159854892"
    
    # Extraer ID
    id_proyecto = extractor.obtener_id_de_url(url_manquel)
    print(f"\nID del proyecto: {id_proyecto}")
    
    if id_proyecto:
        print("\nExtrayendo información del proyecto...")
        print("Esto puede tomar unos segundos...")
        
        resultado = extractor.extraer_resumen_proyecto(id_proyecto)
        
        print("\n📊 RESULTADOS:")
        print("-"*40)
        
        if resultado['resumen']:
            print(f"✅ RESUMEN: {resultado['resumen']}")
            print(f"   Longitud: {len(resultado['resumen'])} caracteres")
        else:
            print("❌ No se encontró resumen detallado")
            
            # Generar resumen descriptivo como fallback
            proyecto_datos = {
                'titulo': 'Parque Fotovoltaico Manquel Solar',
                'tipo': 'DIA',
                'empresa': 'Manquel Solar SpA',
                'region': 'Región del Biobío',
                'comuna': 'Antuco',
                'inversion': 'USD 39.0MM'
            }
            
            resumen_generado = extractor.generar_resumen_descriptivo(proyecto_datos)
            print(f"\n📝 RESUMEN GENERADO: {resumen_generado}")
        
        if resultado['inversion']:
            print(f"\n💰 INVERSIÓN: {resultado['inversion']}")
        
        if resultado['ubicacion']:
            print(f"📍 UBICACIÓN: {resultado['ubicacion']}")
        
        if resultado['titular']:
            print(f"🏢 TITULAR: {resultado['titular']}")