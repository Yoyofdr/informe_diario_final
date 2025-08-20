"""
Servicio para manejo de registro con sistema de RUT
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from alerts.models import Organizacion, Destinatario
from alerts.validators import validar_rut_estricto


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
            Destinatario.objects.create(
                nombre=f"{nombre} {apellido}".strip(),
                email=email,
                telefono=telefono,
                organizacion=org
            )
            
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
            Destinatario.objects.create(
                nombre=f"{nombre} {apellido}".strip(),
                email=email,
                telefono=telefono,
                organizacion=org
            )
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
        Destinatario.objects.create(
            nombre=f"{nombre} {apellido}".strip(),
            email=email,
            telefono=telefono,
            organizacion=org
        )
        
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