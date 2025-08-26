"""
Servicio para manejo de registro con sistema de RUT
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from alerts.models import Organizacion, Destinatario
from alerts.validators import validar_rut_estricto
from alerts.enviar_informe_bienvenida import enviar_informe_bienvenida
import logging

logger = logging.getLogger(__name__)


def handle_signup(
    user: User,
    rut: str | None,
    no_empresa: bool,
    nombre_empresa: str | None,
    email: str,
    nombre: str,
    apellido: str,
    telefono: str | None = None
) -> Organizacion:
    """
    Maneja el registro de un usuario con el nuevo sistema basado en RUT.
    
    Args:
        user: Usuario Django creado
        rut: RUT de la empresa (opcional)
        no_empresa: True si el usuario no pertenece a una empresa
        nombre_empresa: Nombre de la empresa (opcional)
        email: Email del usuario
        nombre: Nombre del usuario
        apellido: Apellido del usuario
        telefono: Teléfono del usuario (opcional)
    
    Returns:
        Organizacion: La organización creada o encontrada
    
    Raises:
        ValidationError: Si los datos no son válidos
    """
    with transaction.atomic():
        # Caso 1: Usuario independiente
        if no_empresa:
            # Crear organización individual
            org = Organizacion.objects.create(
                nombre=f"Espacio de {nombre} {apellido}".strip() or f"Espacio de {user.username}",
                tipo=Organizacion.Tipo.INDEPENDIENTE,
                admin=user,
                dominio=None,  # No usamos dominio
                rut=None  # Independientes no tienen RUT
            )
            
            # Agregar al usuario como destinatario
            destinatario = Destinatario.objects.create(
                nombre=f"{nombre} {apellido}".strip(),
                email=email,
                telefono=telefono,
                organizacion=org
            )
            
            # Enviar correo de bienvenida con información del trial
            try:
                enviar_informe_bienvenida(
                    email_destinatario=email,
                    nombre_destinatario=f"{nombre} {apellido}".strip(),
                    fecha_fin_trial=destinatario.fecha_fin_trial
                )
                logger.info(f"Correo de bienvenida enviado a {email} con trial hasta {destinatario.fecha_fin_trial}")
            except Exception as e:
                logger.error(f"Error enviando correo de bienvenida: {e}")
                # No fallar el registro si el email falla
            
            return org
        
        # Caso 2: Usuario de empresa (requiere RUT)
        if not rut:
            raise ValidationError("Debes ingresar un RUT o marcar 'No pertenezco a una empresa'.")
        
        # Limpiar y validar RUT
        rut = rut.strip()
        validar_rut_estricto(rut)
        
        # Buscar si ya existe una organización con este RUT
        org = Organizacion.objects.filter(rut=rut).first()
        
        if org:
            # La organización ya existe, agregar al usuario como destinatario
            # No cambiamos el admin
            destinatario = Destinatario.objects.create(
                nombre=f"{nombre} {apellido}".strip(),
                email=email,
                telefono=telefono,
                organizacion=org
            )
            
            # Enviar correo de bienvenida con información del trial
            try:
                enviar_informe_bienvenida(
                    email_destinatario=email,
                    nombre_destinatario=f"{nombre} {apellido}".strip(),
                    fecha_fin_trial=destinatario.fecha_fin_trial
                )
                logger.info(f"Correo de bienvenida enviado a {email} con trial hasta {destinatario.fecha_fin_trial}")
            except Exception as e:
                logger.error(f"Error enviando correo de bienvenida: {e}")
                # No fallar el registro si el email falla
            
            return org
        
        # Crear nueva organización de empresa
        org = Organizacion.objects.create(
            nombre=nombre_empresa or f"Empresa {rut}",
            rut=rut,
            tipo=Organizacion.Tipo.EMPRESA,
            admin=user,
            dominio=None  # No usamos dominio
        )
        
        # Agregar al usuario como destinatario
        destinatario = Destinatario.objects.create(
            nombre=f"{nombre} {apellido}".strip(),
            email=email,
            telefono=telefono,
            organizacion=org
        )
        
        # Enviar correo de bienvenida con información del trial
        try:
            enviar_informe_bienvenida(
                email_destinatario=email,
                nombre_destinatario=f"{nombre} {apellido}".strip(),
                fecha_fin_trial=destinatario.fecha_fin_trial
            )
            logger.info(f"Correo de bienvenida enviado a {email} con trial hasta {destinatario.fecha_fin_trial}")
        except Exception as e:
            logger.error(f"Error enviando correo de bienvenida: {e}")
            # No fallar el registro si el email falla
        
        return org


def migrate_existing_organization(org: Organizacion, rut: str | None = None):
    """
    Función helper para migrar organizaciones existentes al nuevo sistema.
    Solo para uso administrativo.
    
    Args:
        org: Organización existente
        rut: RUT a asignar (opcional)
    """
    if rut:
        validar_rut_estricto(rut)
        org.rut = rut
        org.tipo = Organizacion.Tipo.EMPRESA
    else:
        # Si no tiene RUT, es independiente
        org.tipo = Organizacion.Tipo.INDEPENDIENTE
    
    org.save()