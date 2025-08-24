"""
Scraper integrado para datos ambientales (SEA y SMA)
Versión simplificada con datos de ejemplo para desarrollo
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import json
from typing import List, Dict
import random

logger = logging.getLogger(__name__)

class ScraperAmbiental:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9'
        })
    
    def obtener_datos_ambientales(self, dias_atras: int = 7) -> Dict[str, List[Dict]]:
        """
        Obtiene datos ambientales de SEA y SMA
        
        Returns:
            Diccionario con proyectos SEA y sanciones SMA
        """
        datos = {
            'proyectos_sea': self._obtener_proyectos_sea(dias_atras),
            'sanciones_sma': self._obtener_sanciones_sma(dias_atras)
        }
        
        return datos
    
    def _obtener_proyectos_sea(self, dias_atras: int) -> List[Dict]:
        """
        Obtiene proyectos con RCA del SEA
        Por ahora usa datos de ejemplo para desarrollo
        """
        # TODO: Implementar scraping real cuando tengamos acceso correcto a la API
        
        # Datos de ejemplo realistas - SOLO del día anterior si dias_atras=1
        fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
        
        proyectos_ejemplo = [
            {
                'fuente': 'SEA',
                'tipo': 'RCA Aprobada',
                'titulo': 'Parque Fotovoltaico Sol del Norte',
                'empresa': 'Energía Solar Chile S.A.',
                'fecha': fecha_ayer if dias_atras == 1 else (datetime.now() - timedelta(days=2)).strftime('%d/%m/%Y'),
                'region': 'Región de Antofagasta',
                'inversion_mmusd': 120.5,
                'resumen': '✅ APROBADO. Proyecto de energía solar de 100 MW. Inversión: USD 120.5MM en Región de Antofagasta. Generará energía limpia equivalente al consumo de 50,000 hogares.',
                'relevancia': 8.5,
                'url': 'https://seia.sea.gob.cl/expediente/ficha.php?id_expediente=2024123456'
            },
            {
                'fuente': 'SEA',
                'tipo': 'RCA Rechazada',
                'titulo': 'Expansión Minera Cobre Andino',
                'empresa': 'Minera Los Andes Ltda.',
                'fecha': fecha_ayer if dias_atras == 1 else (datetime.now() - timedelta(days=5)).strftime('%d/%m/%Y'),
                'region': 'Región de Atacama',
                'inversion_mmusd': 450.0,
                'resumen': '❌ RECHAZADO. Proyecto minero de expansión. Inversión propuesta: USD 450MM en Región de Atacama. No cumplió con requisitos de mitigación de impacto hídrico.',
                'relevancia': 9.0,
                'url': 'https://seia.sea.gob.cl/expediente/ficha.php?id_expediente=2024123457'
            },
            {
                'fuente': 'SEA',
                'tipo': 'RCA Aprobada con Condiciones',
                'titulo': 'Terminal Portuario Bahía Verde',
                'empresa': 'Puerto Pacífico S.A.',
                'fecha': fecha_ayer,
                'region': 'Región de Valparaíso',
                'inversion_mmusd': 85.0,
                'resumen': '✅ APROBADO CON CONDICIONES. Proyecto portuario. Inversión: USD 85MM en Región de Valparaíso. Debe implementar plan de monitoreo marino continuo.',
                'relevancia': 7.0,
                'url': 'https://seia.sea.gob.cl/expediente/ficha.php?id_expediente=2024123458'
            }
        ]
        
        # Filtrar por fecha si es necesario
        fecha_limite = datetime.now() - timedelta(days=dias_atras)
        proyectos_filtrados = []
        
        for proyecto in proyectos_ejemplo:
            try:
                fecha = datetime.strptime(proyecto['fecha'], '%d/%m/%Y')
                if fecha >= fecha_limite:
                    proyectos_filtrados.append(proyecto)
            except:
                proyectos_filtrados.append(proyecto)
        
        logger.info(f"✅ Obtenidos {len(proyectos_filtrados)} proyectos SEA (datos de ejemplo)")
        return proyectos_filtrados
    
    def _obtener_sanciones_sma(self, dias_atras: int) -> List[Dict]:
        """
        Obtiene sanciones de la SMA
        Por ahora usa datos de ejemplo para desarrollo
        """
        # TODO: Implementar scraping real cuando tengamos acceso correcto a la API
        
        # Datos de ejemplo realistas - SOLO del día anterior si dias_atras=1
        fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
        
        sanciones_ejemplo = [
            {
                'fuente': 'SMA',
                'tipo': 'Sanción Ambiental',
                'titulo': 'Sanción a Industrias Químicas del Sur S.A. - Multa 500 UTA',
                'empresa': 'Industrias Químicas del Sur S.A.',
                'fecha': fecha_ayer if dias_atras == 1 else (datetime.now() - timedelta(days=3)).strftime('%d/%m/%Y'),
                'multa': '500 UTA (~$360M CLP)',
                'expediente': 'D-041-2024',
                'resumen': 'Sanción por vertimiento de residuos industriales sin tratamiento. Superación de norma de emisión en 300%. Estado: Sanción aplicada y en proceso de pago.',
                'relevancia': 8.0,
                'url': 'https://snifa.sma.gob.cl/Sancionatorio/Ficha/2024/D-041-2024'
            },
            {
                'fuente': 'SMA',
                'tipo': 'Resolución Sancionatoria',
                'titulo': 'Multa a Agrícola San Pedro - 150 UTM',
                'empresa': 'Agrícola San Pedro Ltda.',
                'fecha': fecha_ayer if dias_atras == 1 else (datetime.now() - timedelta(days=6)).strftime('%d/%m/%Y'),
                'multa': '150 UTM (~$10M CLP)',
                'expediente': 'F-022-2024',
                'resumen': 'Incumplimiento de plan de manejo de residuos orgánicos. Contaminación de aguas subterráneas detectada en monitoreo.',
                'relevancia': 5.0,
                'url': 'https://snifa.sma.gob.cl/Sancionatorio/Ficha/2024/F-022-2024'
            },
            {
                'fuente': 'SMA',
                'tipo': 'Clausura Temporal',
                'titulo': 'Clausura de Planta Procesadora Los Robles',
                'empresa': 'Procesadora Los Robles S.A.',
                'fecha': fecha_ayer,
                'multa': '1000 UTA (~$720M CLP) + Clausura 30 días',
                'expediente': 'A-003-2024',
                'resumen': 'Clausura temporal y multa por emisiones atmosféricas que superan en 500% la norma. Riesgo grave para salud de la población.',
                'relevancia': 10.0,
                'url': 'https://snifa.sma.gob.cl/Sancionatorio/Ficha/2024/A-003-2024'
            }
        ]
        
        # Filtrar por fecha si es necesario
        fecha_limite = datetime.now() - timedelta(days=dias_atras)
        sanciones_filtradas = []
        
        for sancion in sanciones_ejemplo:
            try:
                fecha = datetime.strptime(sancion['fecha'], '%d/%m/%Y')
                if fecha >= fecha_limite:
                    sanciones_filtradas.append(sancion)
            except:
                sanciones_filtradas.append(sancion)
        
        logger.info(f"✅ Obtenidas {len(sanciones_filtradas)} sanciones SMA (datos de ejemplo)")
        return sanciones_filtradas
    
    def formatear_para_informe(self, datos: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Formatea los datos ambientales para el informe
        """
        # Combinar y ordenar por relevancia
        todos = []
        
        for proyecto in datos.get('proyectos_sea', []):
            todos.append(proyecto)
        
        for sancion in datos.get('sanciones_sma', []):
            todos.append(sancion)
        
        # Ordenar por relevancia
        todos.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
        
        # Separar por categoría para el informe
        resultado = {
            'destacados': todos[:5],  # Los 5 más relevantes
            'proyectos_sea': datos.get('proyectos_sea', []),
            'sanciones_sma': datos.get('sanciones_sma', [])
        }
        
        return resultado


def test_scraper_ambiental():
    """
    Función de prueba del scraper ambiental integrado
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🌍 PRUEBA SCRAPER AMBIENTAL INTEGRADO (SEA + SMA)")
    print("="*70)
    
    scraper = ScraperAmbiental()
    
    # Obtener datos de los últimos 7 días
    print("\n📋 Obteniendo datos ambientales de los últimos 7 días...")
    datos = scraper.obtener_datos_ambientales(dias_atras=7)
    
    # Mostrar proyectos SEA
    print("\n" + "-"*70)
    print("🏗️ PROYECTOS SEA (Resoluciones de Calificación Ambiental)")
    print("-"*70)
    
    for i, proyecto in enumerate(datos['proyectos_sea'], 1):
        print(f"\n{i}. {proyecto['titulo']}")
        print(f"   📅 {proyecto['fecha']} | 🏢 {proyecto['empresa']}")
        print(f"   💰 Inversión: USD {proyecto.get('inversion_mmusd', 0):.1f}MM")
        print(f"   📝 {proyecto['resumen']}")
    
    # Mostrar sanciones SMA
    print("\n" + "-"*70)
    print("⚖️ SANCIONES SMA (Superintendencia del Medio Ambiente)")
    print("-"*70)
    
    for i, sancion in enumerate(datos['sanciones_sma'], 1):
        print(f"\n{i}. {sancion['titulo']}")
        print(f"   📅 {sancion['fecha']} | 🏢 {sancion['empresa']}")
        print(f"   💸 {sancion.get('multa', 'N/A')}")
        print(f"   📝 {sancion['resumen']}")
    
    # Formatear para informe
    print("\n" + "="*70)
    print("📊 DATOS FORMATEADOS PARA INFORME")
    print("="*70)
    
    formateado = scraper.formatear_para_informe(datos)
    
    print("\n⭐ TOP 5 MÁS RELEVANTES:")
    for i, item in enumerate(formateado['destacados'], 1):
        print(f"\n{i}. [{item['fuente']}] {item['titulo']}")
        print(f"   Relevancia: ⭐ {item.get('relevancia', 0):.1f}/10")
    
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA - Datos de ejemplo listos para integración")
    print("="*70)
    print("\nNOTA: Actualmente usando datos de ejemplo. Se actualizará con scraping")
    print("real cuando se confirmen las URLs y estructura de las APIs oficiales.")


if __name__ == "__main__":
    test_scraper_ambiental()