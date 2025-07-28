from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import os
import sys

# Agregar el directorio raíz al path para poder importar los scripts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)

class Command(BaseCommand):
    help = 'Envía los informes diarios del Diario Oficial y CMF a todos los suscriptores activos'

    def handle(self, *args, **options):
        try:
            # Importar el módulo del generador de informes
            import importlib.util
            script_path = os.path.join(BASE_DIR, 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py')
            spec = importlib.util.spec_from_file_location("generar_informe", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Obtener la fecha de hoy
            fecha_hoy = datetime.now().strftime("%d-%m-%Y")
            
            self.stdout.write(f"🚀 Iniciando envío de informes para {fecha_hoy}...")
            
            # Ejecutar el script de generación de informes
            resultado = module.generar_informe_oficial(fecha=fecha_hoy)
            
            if resultado:
                self.stdout.write(self.style.SUCCESS(f"✅ Informes enviados exitosamente para {fecha_hoy}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error al enviar informes para {fecha_hoy}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error crítico: {str(e)}"))
            import traceback
            traceback.print_exc()
            # Re-raise para que Heroku pueda detectar el error
            raise