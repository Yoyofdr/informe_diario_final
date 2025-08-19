"""
Validadores personalizados para la aplicación alerts
"""
import re
from django.core.exceptions import ValidationError


# Expresión regular para RUT estricto: NNNNNNNN-DV (sin puntos, DV en mayúscula)
RUT_STRICT_RE = re.compile(r"^[1-9]\d{0,7}-[0-9K]$")


def calcular_dv(numero: str) -> str:
    """
    Calcula el dígito verificador de un RUT chileno.
    
    Args:
        numero: String con el número del RUT (sin DV)
    
    Returns:
        String con el dígito verificador (0-9 o K)
    """
    s, mult = 0, 2
    for c in reversed(numero):
        s += int(c) * mult
        mult = 2 if mult == 7 else mult + 1
    r = 11 - (s % 11)
    return "0" if r == 11 else ("K" if r == 10 else str(r))


def validar_rut_estricto(value: str):
    """
    Valida un RUT chileno en formato estricto: NNNNNNNN-DV
    - Sin puntos
    - DV en mayúscula (0-9 o K)
    - No permite ceros a la izquierda
    - Valida el dígito verificador
    
    Args:
        value: String con el RUT a validar
    
    Raises:
        ValidationError: Si el formato es inválido o el DV es incorrecto
    """
    if not value:
        return  # Campo opcional, si está vacío es válido
    
    # Validar formato
    if not RUT_STRICT_RE.match(value):
        raise ValidationError(
            "Formato inválido. Usa NNNNNNNN-DV (sin puntos, DV en mayúscula)."
        )
    
    # Separar número y DV
    numero, dv = value.split("-")
    
    # Validar dígito verificador
    if dv != calcular_dv(numero):
        raise ValidationError("Dígito verificador incorrecto.")