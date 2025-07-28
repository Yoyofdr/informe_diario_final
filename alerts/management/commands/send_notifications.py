import time
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from alerts.models import HechoEsencial, PerfilUsuario, NotificacionEnviada, User

class Command(BaseCommand):
    """
    Comando de gestión para enviar notificaciones por correo sobre hechos esenciales no notificados.
    """
    help = 'Envía notificaciones por correo electrónico para nuevos Hechos Esenciales.'

    def handle(self, *args, **options):
        hechos_a_notificar = HechoEsencial.objects.filter(
            notificacion_enviada=False,
            resumen__isnull=False,
            relevancia__isnull=False
        ).select_related('empresa')

        if not hechos_a_notificar.exists():
            self.stdout.write(self.style.SUCCESS('No hay nuevos hechos esenciales analizados para notificar.'))
            return

        notificaciones_enviadas = 0
        usuarios_notificados = set()

        for hecho in hechos_a_notificar:
            empresa = hecho.empresa
            
            perfiles_suscritos = PerfilUsuario.objects.filter(suscripciones=empresa).select_related('user')

            if not perfiles_suscritos.exists():
                hecho.notificacion_enviada = True
                hecho.save()
                continue

            for perfil in perfiles_suscritos:
                usuario = perfil.user
                
                if NotificacionEnviada.objects.filter(usuario=usuario, hecho_esencial=hecho).exists():
                    continue

                if usuario.email:
                    usuarios_notificados.add(usuario)
                    contexto_email = {
                        'nombre_usuario': usuario.username,
                        'hecho_esencial': hecho,
                        'url_absoluta': settings.SITE_URL + reverse('alerts:dashboard') 
                    }
                    cuerpo_html = render_to_string('alerts/email/notificacion_hecho_esencial.html', contexto_email)
                    
                    try:
                        send_mail(
                            subject=f'Alerta de Hecho Esencial: {hecho.empresa.nombre}',
                            message='', 
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[usuario.email],
                            html_message=cuerpo_html,
                            fail_silently=False,
                        )
                        notificaciones_enviadas += 1
                        NotificacionEnviada.objects.create(usuario=usuario, hecho_esencial=hecho)
                    except Exception as e:
                         self.stdout.write(self.style.ERROR(f"Error al enviar email a {usuario.username}: {e}"))


            hecho.notificacion_enviada = True
            hecho.save()

        if notificaciones_enviadas > 0:
            self.stdout.write(self.style.SUCCESS(f'Se enviaron {notificaciones_enviadas} notificaciones a {len(usuarios_notificados)} usuarios.'))
        else:
            self.stdout.write(self.style.SUCCESS('No se requirió enviar nuevas notificaciones.')) 