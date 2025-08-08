from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import os
import sys

# Agregar el directorio raíz al path para poder importar los scripts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)

from alerts.models import Destinatario, InformeDiarioCache

class Command(BaseCommand):
    help = 'Reenvía el informe del día a destinatarios de Barros & Errázuriz'

    def handle(self, *args, **options):
        try:
            # Obtener destinatarios BYE
            destinatarios_bye = Destinatario.objects.filter(email__endswith='@bye.cl')
            self.stdout.write(f"\n🔍 Encontrados {destinatarios_bye.count()} destinatarios de Barros & Errázuriz:")
            for dest in destinatarios_bye:
                self.stdout.write(f"   - {dest.email} ({dest.nombre})")
            
            if not destinatarios_bye.exists():
                self.stdout.write(self.style.WARNING("No hay destinatarios de BYE registrados"))
                return
            
            # Verificar si hay informe en caché para hoy
            fecha_hoy = datetime.now().strftime("%d-%m-%Y")
            informe_cache = InformeDiarioCache.objects.filter(fecha=datetime.now().date()).first()
            
            if not informe_cache:
                self.stdout.write(self.style.ERROR(f"❌ No hay informe en caché para {fecha_hoy}"))
                self.stdout.write("Generando informe nuevo...")
                
                # Importar el generador
                import importlib.util
                script_path = os.path.join(BASE_DIR, 'scripts', 'generators', 'generar_informe_oficial_integrado_mejorado.py')
                spec = importlib.util.spec_from_file_location("generar_informe", script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Generar informe (esto también lo guarda en caché)
                module.generar_informe_oficial(fecha=fecha_hoy)
                
                # Obtener el informe recién generado
                informe_cache = InformeDiarioCache.objects.filter(fecha=datetime.now().date()).first()
            
            if informe_cache and informe_cache.contenido_html:
                self.stdout.write(self.style.SUCCESS(f"✅ Informe encontrado en caché"))
                
                # Configurar variable temporal para enviar solo a BYE
                os.environ['ENVIO_SOLO_BYE'] = 'true'
                
                # Enviar el informe desde caché
                from scripts.generators.generar_informe_oficial_integrado_mejorado import enviar_informe_email
                
                # Crear lista solo con emails BYE
                emails_bye = list(destinatarios_bye.values_list('email', flat=True))
                
                self.stdout.write(f"\n📧 Reenviando informe a {len(emails_bye)} destinatarios de BYE...")
                
                # Modificar temporalmente la función para usar solo estos destinatarios
                import scripts.generators.generar_informe_oficial_integrado_mejorado as gen_module
                original_func = gen_module.enviar_informe_email
                
                def enviar_solo_bye(html, fecha):
                    # Configuración desde variables de entorno
                    from email.mime.text import MIMEText
                    from email.mime.multipart import MIMEMultipart
                    import smtplib
                    import logging
                    
                    de_email = 'contacto@informediariochile.cl'
                    password = os.getenv('HOSTINGER_EMAIL_PASSWORD', '')
                    smtp_server = os.getenv('SMTP_SERVER', 'smtp.hostinger.com')
                    smtp_port = int(os.getenv('SMTP_PORT', '587'))
                    
                    if not password:
                        self.stdout.write(self.style.ERROR("❌ Error: No se encontró la contraseña del email"))
                        return
                    
                    # Formatear fecha
                    from datetime import datetime
                    fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
                    fecha_formato = module.formatear_fecha_espanol(fecha_obj)
                    
                    try:
                        server = smtplib.SMTP(smtp_server, smtp_port)
                        server.starttls()
                        server.login(de_email, password)
                        
                        enviados = 0
                        errores = 0
                        
                        for email_destinatario in emails_bye:
                            msg = MIMEMultipart('alternative')
                            msg['From'] = de_email
                            msg['To'] = email_destinatario
                            msg['Subject'] = f"Informe Diario • {fecha_formato} (REENVÍO)"
                            
                            html_part = MIMEText(html, 'html', 'utf-8')
                            msg.attach(html_part)
                            
                            try:
                                server.send_message(msg)
                                enviados += 1
                                self.stdout.write(self.style.SUCCESS(f"✅ Enviado a: {email_destinatario}"))
                            except Exception as e:
                                errores += 1
                                self.stdout.write(self.style.ERROR(f"❌ Error enviando a {email_destinatario}: {str(e)}"))
                        
                        server.quit()
                        
                        self.stdout.write(f"\n📊 RESUMEN DE REENVÍO:")
                        self.stdout.write(f"   ✅ Enviados exitosamente: {enviados}")
                        self.stdout.write(f"   ❌ Errores: {errores}")
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error crítico: {str(e)}"))
                
                # Ejecutar envío
                enviar_solo_bye(informe_cache.contenido_html, fecha_hoy)
                
                # Limpiar variable temporal
                os.environ.pop('ENVIO_SOLO_BYE', None)
                
            else:
                self.stdout.write(self.style.ERROR("❌ No se pudo obtener el informe"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error crítico: {str(e)}"))
            import traceback
            traceback.print_exc()