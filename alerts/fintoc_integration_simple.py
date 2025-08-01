"""
Integración simplificada con Fintoc (sin Firebase para desarrollo)
"""
import os
from datetime import datetime
from fintoc import Fintoc
from django.conf import settings
from typing import Optional, Dict, Any
import json

# Inicializar Fintoc
fintoc_client = Fintoc(os.environ.get('FINTOC_SECRET_KEY'))

# Almacenamiento temporal en archivo (solo para desarrollo)
STORAGE_FILE = 'bank_validations_dev.json'


class FintocIntegrationSimple:
    """Clase simplificada para manejar la integración con Fintoc"""
    
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
    def create_link_token(user_email: str, user_id: int) -> Optional[str]:
        """
        Crea un link token para que el usuario conecte su cuenta bancaria
        """
        try:
            # Crear link en Fintoc
            link = fintoc_client.link_intents.create(
                product='movements',
                country='cl',
                holder_type='individual',
                webhook_url=f"{settings.SITE_URL}/alerts/webhooks/fintoc/",
                widget_token=os.environ.get('FINTOC_PUBLIC_KEY')
            )
            
            # Guardar en almacenamiento local
            data = FintocIntegrationSimple._load_data()
            data[str(user_id)] = {
                'email': user_email,
                'link_token': link.id,
                'widget_token': link.widget_token,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            FintocIntegrationSimple._save_data(data)
            
            return link.widget_token
            
        except Exception as e:
            print(f"Error creando link token: {e}")
            return None
    
    @staticmethod
    def update_bank_connection(user_id: int, link_token: str, account_data: Dict[str, Any]) -> bool:
        """
        Actualiza la información de conexión bancaria cuando se completa
        """
        try:
            data = FintocIntegrationSimple._load_data()
            
            if str(user_id) in data:
                data[str(user_id)].update({
                    'status': 'connected',
                    'bank_name': account_data.get('institution', {}).get('name'),
                    'account_holder': account_data.get('holder_name'),
                    'account_number': account_data.get('number', '')[-4:],  # Solo últimos 4 dígitos
                    'account_type': account_data.get('type'),
                    'connected_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })
                FintocIntegrationSimple._save_data(data)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error actualizando conexión bancaria: {e}")
            return False
    
    @staticmethod
    def get_validation_status(user_id: int) -> Dict[str, Any]:
        """
        Obtiene el estado de validación bancaria de un usuario
        """
        try:
            data = FintocIntegrationSimple._load_data()
            
            if str(user_id) in data:
                return data[str(user_id)]
            
            return {
                'status': 'not_started',
                'message': 'No se ha iniciado la validación bancaria'
            }
            
        except Exception as e:
            print(f"Error obteniendo estado de validación: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def disconnect_account(user_id: int) -> bool:
        """
        Desconecta la cuenta bancaria del usuario
        """
        try:
            data = FintocIntegrationSimple._load_data()
            
            if str(user_id) in data:
                data[str(user_id)].update({
                    'status': 'disconnected',
                    'disconnected_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })
                FintocIntegrationSimple._save_data(data)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error desconectando cuenta: {e}")
            return False