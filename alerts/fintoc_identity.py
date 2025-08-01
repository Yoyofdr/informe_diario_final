"""
Integración con Fintoc para validación de identidad (sin cuentas bancarias)
"""
import os
from datetime import datetime
from fintoc import Fintoc
from django.conf import settings
from typing import Optional, Dict, Any
import json

# Inicializar Fintoc
fintoc_client = Fintoc(os.environ.get('FINTOC_SECRET_KEY'))

# Almacenamiento temporal para desarrollo
STORAGE_FILE = 'identity_validations_dev.json'


class FintocIdentityValidation:
    """Clase para manejar solo la validación de identidad con Fintoc"""
    
    @staticmethod
    def _load_data() -> dict:
        """Carga datos del archivo de almacenamiento"""
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def _save_data(data: dict):
        """Guarda datos en el archivo de almacenamiento"""
        with open(STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def create_validation_link(user_email: str, user_id: int, rut: str = None) -> Optional[str]:
        """
        Crea un link para validar la identidad del usuario
        Solo pedirá datos personales, NO cuentas bancarias
        """
        try:
            # Crear link en Fintoc con producto de identidad
            link = fintoc_client.link_intents.create(
                product='identity',  # Solo validación de identidad
                country='cl',
                holder_type='individual',
                webhook_url=f"{settings.SITE_URL}/alerts/webhooks/fintoc-identity/",
                widget_token=os.environ.get('FINTOC_PUBLIC_KEY')
            )
            
            # Guardar en almacenamiento local
            data = FintocIdentityValidation._load_data()
            data[str(user_id)] = {
                'email': user_email,
                'rut': rut,
                'link_token': link.id,
                'widget_token': link.widget_token,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            FintocIdentityValidation._save_data(data)
            
            return link.widget_token
            
        except Exception as e:
            print(f"Error creando link de validación: {e}")
            return None
    
    @staticmethod
    def update_validation_status(user_id: int, validation_data: Dict[str, Any]) -> bool:
        """
        Actualiza el estado de validación cuando se completa
        Solo guarda datos de identidad, NO información bancaria
        """
        try:
            data = FintocIdentityValidation._load_data()
            
            if str(user_id) in data:
                data[str(user_id)].update({
                    'status': 'validated',
                    'full_name': validation_data.get('full_name'),
                    'rut': validation_data.get('rut'),
                    'validated_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })
                FintocIdentityValidation._save_data(data)
                
                # Actualizar el modelo de Organización si es necesario
                from alerts.models import Organizacion
                try:
                    org = Organizacion.objects.get(admin_id=user_id)
                    org.validacion_bancaria = 'connected'  # Usamos el mismo campo pero significa "identidad validada"
                    org.fecha_validacion_bancaria = datetime.now()
                    org.save()
                except Organizacion.DoesNotExist:
                    pass
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error actualizando validación: {e}")
            return False
    
    @staticmethod
    def get_validation_status(user_id: int) -> Dict[str, Any]:
        """
        Obtiene el estado de validación de identidad de un usuario
        """
        try:
            data = FintocIdentityValidation._load_data()
            
            if str(user_id) in data:
                validation = data[str(user_id)]
                return {
                    'status': validation.get('status'),
                    'full_name': validation.get('full_name'),
                    'rut': validation.get('rut'),
                    'validated_at': validation.get('validated_at'),
                    'message': 'Identidad validada' if validation.get('status') == 'validated' else 'Validación pendiente'
                }
            
            return {
                'status': 'not_started',
                'message': 'No se ha iniciado la validación de identidad'
            }
            
        except Exception as e:
            print(f"Error obteniendo estado de validación: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def is_user_validated(user_id: int) -> bool:
        """
        Verifica si un usuario tiene su identidad validada
        """
        status = FintocIdentityValidation.get_validation_status(user_id)
        return status.get('status') == 'validated'