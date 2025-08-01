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

        # Programar el envío del informe diario a las 9:00 AM
        schedule.every().day.at("09:00").do(job, task_name="Envío Informe Diario Oficial", command_name='informe_diario_oficial')

        # Puedes mantener otras tareas si lo deseas
        # schedule.every(30).minutes.do(job, task_name="Scraping de Hechos Esenciales", command_name='scrape_hechos')
        # schedule.every(30).minutes.do(job, task_name="Envío de Notificaciones", command_name='send_notifications')

        self.stdout.write(self.style.SUCCESS('Tarea programada para ejecutarse todos los días a las 9:00 AM.'))
        self.stdout.write(self.style.SUCCESS('Presiona CTRL+C para detener el programador.'))

        while True:
            schedule.run_pending()
            time.sleep(30) 