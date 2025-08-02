from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from alerts.scraper_diario_oficial import obtener_sumario_diario_oficial
from alerts.informe_diario import generar_informe_html
from datetime import datetime
from django.conf import settings
from alerts.models import Destinatario, Organizacion, Empresa, InformeEnviado

class Command(BaseCommand):
    help = 'Genera el informe diario del Diario Oficial y lo envía por correo a todos los destinatarios.'

    def add_arguments(self, parser):
        parser.add_argument('--fecha', type=str, help='Fecha en formato dd-mm-aaaa (opcional)')
        parser.add_argument('--test', action='store_true', help='Modo test visual')
        parser.add_argument('--force', action='store_true', help='Forzar refresco del scraping, ignorando caché')

    def handle(self, *args, **options):
        fecha = options.get('fecha')
        force = options.get('force', False)
        from_email = 'contacto@informediariochile.cl'  # Usar email configurado en el servidor SMTP
        destinatarios = Destinatario.objects.values_list('email', flat=True)
        if not destinatarios:
            self.stdout.write(self.style.WARNING('No hay destinatarios registrados.'))
            return

        if options.get('test'):
            # Datos de ejemplo para el test visual
            publicaciones = [
                {
                    'titulo': 'Ejemplo de hecho relevante',
                    'resumen': 'Este es un resumen de ejemplo para mostrar el diseño del informe diario.',
                    'url_pdf': 'https://www.diariooficial.interior.gob.cl/documento/ejemplo.pdf',
                    'categoria': 'otros',
                }
            ]
            valores_monedas = {'dolar': '950,00', 'euro': '1050,00'}
            total_documentos = 1
            tiempo_lectura = max(1, total_documentos // 4)
            html = generar_informe_html(publicaciones, fecha, valores_monedas, documentos_analizados=total_documentos, tiempo_lectura=tiempo_lectura)
            text = "Informe Diario Oficial (prueba): ver versión HTML."
        else:
            sumario = obtener_sumario_diario_oficial(fecha=fecha, force_refresh=force) if fecha else obtener_sumario_diario_oficial(force_refresh=force)
            publicaciones = sumario["publicaciones"]
            valores_monedas = sumario["valores_monedas"]
            total_documentos = sumario.get("total_documentos", None)
            if total_documentos is None:
                total_documentos = len(publicaciones)
            tiempo_lectura = max(1, total_documentos // 4)
            url_informe_completo = "https://informediario.cl/informe-completo"  # Puedes personalizar esto
            # Siempre enviar el informe, incluso si no hay publicaciones
            if not publicaciones:
                print("[INFO] No se encontraron publicaciones relevantes para hoy.")
            html = generar_informe_html(publicaciones, fecha, valores_monedas, documentos_analizados=total_documentos, tiempo_lectura=tiempo_lectura, url_informe_completo=url_informe_completo)
            text = f"Informe Diario Oficial {fecha or ''}: ver versión HTML."

        subject = f"Informe Diario Oficial - {fecha or datetime.now().strftime('%d-%m-%Y')}"
        
        # ENVIAR A TODOS LOS DESTINATARIOS SIN IMPORTAR SI TIENEN EMPRESA
        destinatarios_enviados = []
        destinatarios_por_org = {}
        
        # Obtener todos los destinatarios
        for dest in Destinatario.objects.select_related('organizacion').all():
            email = dest.email
            org_nombre = dest.organizacion.nombre if dest.organizacion else "Sin organización"
            
            # Enviar email
            try:
                msg = EmailMultiAlternatives(subject, text, from_email, [email])
                msg.attach_alternative(html, "text/html")
                msg.send()
                self.stdout.write(self.style.SUCCESS(f"✅ Correo enviado a {email} ({org_nombre})"))
                destinatarios_enviados.append(email)
                
                # Agrupar por organización para el registro
                if org_nombre not in destinatarios_por_org:
                    destinatarios_por_org[org_nombre] = []
                destinatarios_por_org[org_nombre].append(email)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error enviando a {email}: {str(e)}"))
        
        # Guardar registro general de envío (sin depender de Empresa)
        if destinatarios_enviados:
            # Buscar si existe alguna empresa para mantener compatibilidad
            empresa_default = Empresa.objects.first()
            if not empresa_default:
                # Crear empresa por defecto si no existe ninguna
                empresa_default = Empresa.objects.create(
                    nombre="Informe Diario"
                )
            
            InformeEnviado.objects.create(
                empresa=empresa_default,
                destinatarios=", ".join(destinatarios_enviados),
                enlace_html="",
                resumen=f"{text} - Enviado a {len(destinatarios_enviados)} destinatarios"
            )
        
        self.stdout.write(self.style.SUCCESS(f"\n📧 Total de correos enviados: {len(destinatarios_enviados)}")) 