#!/usr/bin/env python3
"""
Generador de resúmenes mejorados para proyectos SEA
NO intenta conectarse al SEA - solo mejora los resúmenes existentes
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class SEAResumenGenerador:
    """
    Genera resúmenes mejorados basándose en la información disponible del proyecto
    NO realiza conexiones externas
    """
    
    def mejorar_resumen(self, proyecto: Dict) -> str:
        """
        Mejora el resumen de un proyecto basándose en los datos disponibles
        
        Args:
            proyecto: Diccionario con datos del proyecto (titulo, tipo, empresa, region, etc.)
            
        Returns:
            Resumen mejorado del proyecto
        """
        titulo = proyecto.get('titulo', '')
        empresa = proyecto.get('empresa', proyecto.get('titular', ''))
        region = proyecto.get('region', '')
        comuna = proyecto.get('comuna', '')
        tipo = proyecto.get('tipo', '')  # DIA o EIA
        inversion = proyecto.get('inversion', '')
        
        if not titulo:
            return proyecto.get('resumen', '')
        
        # Analizar el título para identificar el tipo de proyecto
        titulo_lower = titulo.lower()
        
        # === PROYECTOS DE ENERGÍA ===
        if any(palabra in titulo_lower for palabra in ['fotovoltaico', 'solar', 'fotovoltaica']):
            resumen = self._generar_resumen_solar(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        elif any(palabra in titulo_lower for palabra in ['eólico', 'eólica', 'aerogenerador', 'viento']):
            resumen = self._generar_resumen_eolico(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        elif 'termoeléctrica' in titulo_lower or 'central térmica' in titulo_lower:
            resumen = self._generar_resumen_termoelectrica(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        elif 'hidroeléctrica' in titulo_lower or 'central hidráulica' in titulo_lower:
            resumen = self._generar_resumen_hidroelectrica(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        # === PROYECTOS MINEROS ===
        elif any(palabra in titulo_lower for palabra in ['minero', 'mina', 'extracción', 'explotación']):
            resumen = self._generar_resumen_minero(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        # === PROYECTOS INMOBILIARIOS ===
        elif any(palabra in titulo_lower for palabra in ['inmobiliario', 'habitacional', 'vivienda', 'condominio', 'edificio']):
            resumen = self._generar_resumen_inmobiliario(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        # === INFRAESTRUCTURA ===
        elif any(palabra in titulo_lower for palabra in ['puerto', 'terminal', 'muelle', 'portuario']):
            resumen = self._generar_resumen_portuario(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        elif any(palabra in titulo_lower for palabra in ['carretera', 'ruta', 'camino', 'vial', 'autopista']):
            resumen = self._generar_resumen_vial(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        elif 'línea' in titulo_lower and ('transmisión' in titulo_lower or 'eléctrica' in titulo_lower):
            resumen = self._generar_resumen_linea_transmision(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        # === PLANTAS DE TRATAMIENTO ===
        elif 'planta' in titulo_lower:
            resumen = self._generar_resumen_planta(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        # === PROYECTOS ACUÍCOLAS ===
        elif any(palabra in titulo_lower for palabra in ['acuícola', 'salmón', 'cultivo', 'piscicultura']):
            resumen = self._generar_resumen_acuicola(titulo_lower, tipo, empresa, region, comuna, inversion)
        
        # === OTROS PROYECTOS ===
        else:
            resumen = self._generar_resumen_generico(titulo, tipo, empresa, region, comuna, inversion)
        
        return resumen
    
    def _generar_resumen_solar(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para proyecto solar"""
        # Buscar capacidad en el título
        capacidad_match = re.search(r'(\d+[\.,]?\d*)\s*(mw|megawatt|gwh|mwp)', titulo, re.I)
        capacidad = capacidad_match.group(0) if capacidad_match else None
        
        if capacidad:
            resumen = f"Proyecto de generación de energía solar fotovoltaica con capacidad de {capacidad}"
        else:
            resumen = "Proyecto de generación de energía solar fotovoltaica"
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_eolico(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para proyecto eólico"""
        capacidad_match = re.search(r'(\d+[\.,]?\d*)\s*(mw|megawatt)', titulo, re.I)
        turbinas_match = re.search(r'(\d+)\s*(aerogenerador|turbina)', titulo, re.I)
        
        if capacidad_match and turbinas_match:
            resumen = f"Parque eólico de {capacidad_match.group(0)} con {turbinas_match.group(0)}"
        elif capacidad_match:
            resumen = f"Parque eólico con capacidad de {capacidad_match.group(0)}"
        elif turbinas_match:
            resumen = f"Parque eólico con {turbinas_match.group(0)}"
        else:
            resumen = "Proyecto de generación de energía eólica"
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_termoelectrica(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para central termoeléctrica"""
        capacidad_match = re.search(r'(\d+[\.,]?\d*)\s*(mw|megawatt)', titulo, re.I)
        
        if 'gas' in titulo:
            combustible = "a gas natural"
        elif 'carbón' in titulo:
            combustible = "a carbón"
        elif 'biomasa' in titulo:
            combustible = "a biomasa"
        elif 'diesel' in titulo or 'diésel' in titulo:
            combustible = "a diésel"
        else:
            combustible = ""
        
        if capacidad_match:
            resumen = f"Central termoeléctrica {combustible} de {capacidad_match.group(0)}".strip()
        else:
            resumen = f"Central termoeléctrica {combustible}".strip()
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_hidroelectrica(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para central hidroeléctrica"""
        capacidad_match = re.search(r'(\d+[\.,]?\d*)\s*(mw|megawatt)', titulo, re.I)
        
        if 'pasada' in titulo:
            tipo_central = "de pasada"
        elif 'embalse' in titulo:
            tipo_central = "con embalse"
        else:
            tipo_central = ""
        
        if capacidad_match:
            resumen = f"Central hidroeléctrica {tipo_central} de {capacidad_match.group(0)}".strip()
        else:
            resumen = f"Central hidroeléctrica {tipo_central}".strip()
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_minero(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para proyecto minero"""
        if 'áridos' in titulo:
            resumen = "Proyecto de extracción y procesamiento de áridos"
        elif 'cobre' in titulo:
            resumen = "Proyecto minero de cobre"
        elif 'oro' in titulo:
            resumen = "Proyecto minero de oro"
        elif 'litio' in titulo:
            resumen = "Proyecto de extracción de litio"
        elif 'hierro' in titulo:
            resumen = "Proyecto minero de hierro"
        elif 'caliza' in titulo:
            resumen = "Proyecto de extracción de caliza"
        else:
            resumen = "Proyecto de explotación minera"
        
        # Buscar producción si está en el título
        produccion_match = re.search(r'(\d+[\.,]?\d*)\s*(ton|tonelada|tpd|tpm|tpa)', titulo, re.I)
        if produccion_match:
            resumen += f" con capacidad de {produccion_match.group(0)}"
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_inmobiliario(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para proyecto inmobiliario"""
        # Buscar número de unidades
        unidades_match = re.search(r'(\d+)\s*(vivienda|unidad|departamento|casa|lote)', titulo, re.I)
        hectareas_match = re.search(r'(\d+[\.,]?\d*)\s*(ha|hectárea)', titulo, re.I)
        
        if 'condominio' in titulo:
            tipo_proyecto = "Condominio"
        elif 'edificio' in titulo:
            tipo_proyecto = "Edificio habitacional"
        elif 'loteo' in titulo:
            tipo_proyecto = "Loteo"
        elif 'conjunto' in titulo:
            tipo_proyecto = "Conjunto habitacional"
        else:
            tipo_proyecto = "Proyecto inmobiliario"
        
        if unidades_match:
            resumen = f"{tipo_proyecto} de {unidades_match.group(0)}"
        elif hectareas_match:
            resumen = f"{tipo_proyecto} en {hectareas_match.group(0)}"
        else:
            resumen = tipo_proyecto
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_portuario(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para proyecto portuario"""
        if 'ampliación' in titulo:
            resumen = "Ampliación de infraestructura portuaria"
        elif 'terminal' in titulo:
            if 'graneles' in titulo:
                resumen = "Terminal portuario de graneles"
            elif 'contenedores' in titulo:
                resumen = "Terminal portuario de contenedores"
            else:
                resumen = "Terminal portuario"
        elif 'muelle' in titulo:
            resumen = "Construcción de muelle"
        else:
            resumen = "Proyecto de infraestructura portuaria"
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_vial(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para proyecto vial"""
        km_match = re.search(r'(\d+[\.,]?\d*)\s*km', titulo, re.I)
        
        if 'mejoramiento' in titulo:
            tipo_obra = "Mejoramiento vial"
        elif 'ampliación' in titulo:
            tipo_obra = "Ampliación vial"
        elif 'bypass' in titulo or 'by pass' in titulo:
            tipo_obra = "Construcción de bypass"
        elif 'puente' in titulo:
            tipo_obra = "Construcción de puente"
        elif 'autopista' in titulo:
            tipo_obra = "Autopista"
        else:
            tipo_obra = "Proyecto vial"
        
        if km_match:
            resumen = f"{tipo_obra} de {km_match.group(0)}"
        else:
            resumen = tipo_obra
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_linea_transmision(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para línea de transmisión"""
        kv_match = re.search(r'(\d+)\s*kv', titulo, re.I)
        km_match = re.search(r'(\d+[\.,]?\d*)\s*km', titulo, re.I)
        
        if kv_match and km_match:
            resumen = f"Línea de transmisión eléctrica de {kv_match.group(0)} con {km_match.group(0)} de extensión"
        elif kv_match:
            resumen = f"Línea de transmisión eléctrica de {kv_match.group(0)}"
        elif km_match:
            resumen = f"Línea de transmisión eléctrica de {km_match.group(0)}"
        else:
            resumen = "Línea de transmisión eléctrica"
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_planta(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para plantas de tratamiento o industriales"""
        if 'tratamiento' in titulo:
            if 'agua' in titulo or 'aguas servidas' in titulo or 'riles' in titulo:
                resumen = "Planta de tratamiento de aguas"
            elif 'residuo' in titulo or 'basura' in titulo:
                resumen = "Planta de tratamiento de residuos"
            else:
                resumen = "Planta de tratamiento"
        elif 'desaladora' in titulo or 'desalinizadora' in titulo:
            resumen = "Planta desaladora"
        elif 'reciclaje' in titulo:
            resumen = "Planta de reciclaje"
        elif 'procesamiento' in titulo:
            resumen = "Planta de procesamiento industrial"
        elif 'almacenamiento' in titulo:
            resumen = "Planta de almacenamiento"
        else:
            resumen = "Planta industrial"
        
        # Buscar capacidad
        capacidad_match = re.search(r'(\d+[\.,]?\d*)\s*(m3/día|l/s|ton/día|ton/año)', titulo, re.I)
        if capacidad_match:
            resumen += f" con capacidad de {capacidad_match.group(0)}"
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_acuicola(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen para proyecto acuícola"""
        if 'salmón' in titulo or 'salmónidos' in titulo:
            resumen = "Centro de cultivo de salmónidos"
        elif 'mitílidos' in titulo or 'mejillones' in titulo:
            resumen = "Centro de cultivo de mitílidos"
        elif 'algas' in titulo:
            resumen = "Centro de cultivo de algas"
        elif 'piscicultura' in titulo:
            resumen = "Piscicultura"
        else:
            resumen = "Centro de cultivo acuícola"
        
        # Buscar producción
        produccion_match = re.search(r'(\d+[\.,]?\d*)\s*(ton|tonelada)', titulo, re.I)
        if produccion_match:
            resumen += f" con producción de {produccion_match.group(0)}/año"
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _generar_resumen_generico(self, titulo: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Genera resumen genérico para proyectos no categorizados"""
        # Usar parte del título si es descriptivo
        if len(titulo) < 80:
            resumen = titulo
        else:
            # Tomar las primeras palabras significativas
            palabras = titulo.split()[:8]
            resumen = ' '.join(palabras)
            if len(palabras) < len(titulo.split()):
                resumen += '...'
        
        return self._agregar_datos_comunes(resumen, tipo, empresa, region, comuna, inversion)
    
    def _agregar_datos_comunes(self, resumen_base: str, tipo: str, empresa: str, region: str, comuna: str, inversion: str) -> str:
        """Agrega información común al resumen base"""
        # Agregar tipo de evaluación si es relevante
        if tipo == 'EIA':
            resumen_base = f"{resumen_base} (Estudio de Impacto Ambiental)"
        
        # Agregar empresa
        if empresa:
            resumen_base += f", presentado por {empresa}"
        
        # Agregar ubicación
        ubicacion_parts = []
        if comuna:
            ubicacion_parts.append(f"comuna de {comuna}")
        if region:
            ubicacion_parts.append(region)
        
        if ubicacion_parts:
            resumen_base += f", ubicado en {', '.join(ubicacion_parts)}"
        
        # Agregar inversión
        if inversion:
            # Formatear inversión
            if 'USD' in inversion or 'US$' in inversion or 'dólar' in inversion.lower():
                resumen_base += f". Inversión: {inversion}"
            elif 'MM' in inversion or 'millón' in inversion.lower() or 'millones' in inversion.lower():
                resumen_base += f". Inversión: {inversion}"
            elif re.search(r'\d', inversion):
                resumen_base += f". Inversión: {inversion}"
        
        return resumen_base


# Instancia global
sea_resumen_generador = SEAResumenGenerador()


if __name__ == "__main__":
    # Pruebas
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*80)
    print("🧪 PRUEBAS DEL GENERADOR DE RESÚMENES")
    print("="*80)
    
    generador = SEAResumenGenerador()
    
    # Casos de prueba
    proyectos_prueba = [
        {
            'titulo': 'Parque Fotovoltaico Manquel Solar',
            'tipo': 'DIA',
            'empresa': 'Manquel Solar SpA',
            'region': 'Región del Biobío',
            'comuna': 'Antuco',
            'inversion': 'USD 39.0MM'
        },
        {
            'titulo': 'Parque Eólico Los Vientos 150MW',
            'tipo': 'EIA',
            'empresa': 'Energía Renovable S.A.',
            'region': 'Región de La Araucanía',
            'comuna': 'Victoria',
            'inversion': 'USD 180MM'
        },
        {
            'titulo': 'Extracción de Áridos Río Maipo',
            'tipo': 'DIA',
            'empresa': 'Áridos del Maipo Ltda.',
            'region': 'Región Metropolitana',
            'comuna': 'San José de Maipo',
            'inversion': 'USD 5MM'
        },
        {
            'titulo': 'Conjunto Habitacional Vista Hermosa 350 viviendas',
            'tipo': 'DIA',
            'empresa': 'Inmobiliaria Vista S.A.',
            'region': 'Región de Valparaíso',
            'comuna': 'Quilpué',
            'inversion': 'UF 500.000'
        },
        {
            'titulo': 'Línea de Transmisión 220kV Central-Subestación 45km',
            'tipo': 'DIA',
            'empresa': 'Transmisora Eléctrica S.A.',
            'region': 'Región del Maule',
            'comuna': 'Talca',
            'inversion': 'USD 25MM'
        }
    ]
    
    for i, proyecto in enumerate(proyectos_prueba, 1):
        print(f"\n{i}. Proyecto: {proyecto['titulo']}")
        print("-"*60)
        resumen = generador.mejorar_resumen(proyecto)
        print(f"Resumen generado:\n{resumen}")
    
    print("\n" + "="*80)