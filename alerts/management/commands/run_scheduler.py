import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
import schedule
import datetime
import logging

# Configurar logging a archivo
logging.basicConfig(filename='scheduler.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def job(task_name, command_name):
    """Ejecuta un comando de Django y registra la hora."""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Verificar si es domingo (6 = domingo)
    if datetime.datetime.now().weekday() == 6:
        print(f"[{current_time}] SALTANDO tarea '{task_name}' - Es domingo")
        logging.info(f"SALTANDO tarea '{task_name}' - Es domingo")
        return
    
    print(f"[{current_time}] Iniciando tarea: '{task_name}'...")
    logging.info(f"Iniciando tarea: '{task_name}'...")
    try:
        call_command(command_name)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] Tarea '{task_name}' finalizada exitosamente.")
        logging.info(f"Tarea '{task_name}' finalizada exitosamente.")
    except Exception as e:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] Error al ejecutar la tarea '{task_name}': {e}")
        logging.error(f"Error al ejecutar la tarea '{task_name}': {e}")


class Command(BaseCommand):
    help = 'Inicia el programador de tareas para buscar y notificar hechos esenciales.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando el programador...'))

        # Programar el envío del informe diario a las 9:00 AM hora de Chile
        # Heroku usa UTC, Chile es UTC-3 en verano y UTC-4 en invierno
        # Para las 9:00 AM Chile, programamos a las 12:00 UTC (verano) o 13:00 UTC (invierno)
        # Usamos 12:00 UTC que es 9:00 AM en horario de verano de Chile
        schedule.every().day.at("12:00").do(job, task_name="Envío Informe Diario Oficial", command_name='enviar_informes_diarios')

        # Puedes mantener otras tareas si lo deseas
        # schedule.every(30).minutes.do(job, task_name="Scraping de Hechos Esenciales", command_name='scrape_hechos')
        # schedule.every(30).minutes.do(job, task_name="Envío de Notificaciones", command_name='send_notifications')

        self.stdout.write(self.style.SUCCESS('Tarea programada para ejecutarse todos los días a las 12:00 UTC (9:00 AM Chile).'))
        self.stdout.write(self.style.SUCCESS('Presiona CTRL+C para detener el programador.'))

        while True:
            schedule.run_pending()
            time.sleep(30) 