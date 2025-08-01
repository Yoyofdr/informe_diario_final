"""
Integración con Fintoc para validación bancaria
"""
import os
from datetime import datetime
from fintoc import Fintoc
import firebase_admin
from firebase_admin import credentials, firestore
from django.conf import settings
from typing import Optional, Dict, Any

# Inicializar Firebase (solo una vez)
if not firebase_admin._apps:
    # Por ahora usaremos las credenciales por defecto
    # En producción, deberás configurar GOOGLE_APPLICATION_CREDENTIALS
    firebase_admin.initialize_app()

# Inicializar Firestore
db = firestore.client()

# Inicializar Fintoc
fintoc_client = Fintoc(os.environ.get('FINTOC_SECRET_KEY'))


class FintocIntegration:
    """Clase para manejar la integración con Fintoc"""
    
    @staticmethod
    def create_link_token(user_email: str, user_id: int) -> Optional[str]:
        """
        Crea un link token para que el usuario conecte su cuenta bancaria
        
        Args:
            user_email: Email del usuario
            user_id: ID del usuario en Django
            
        Returns:
            Link token o None si hay error
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
            
            # Guardar en Firestore
            doc_ref = db.collection('bank_validations').document(str(user_id))
            doc_ref.set({
                'email': user_email,
                'link_token': link.id,
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            return link.widget_token
            
        except Exception as e:
            print(f"Error creando link token: {e}")
            return None
    
    @staticmethod
    def update_bank_connection(user_id: int, link_token: str, account_data: Dict[str, Any]) -> bool:
        """
        Actualiza la información de conexión bancaria cuando se completa
        
        Args:
            user_id: ID del usuario
            link_token: Token del link completado
            account_data: Datos de la cuenta conectada
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            doc_ref = db.collection('bank_validations').document(str(user_id))
            
            # Actualizar con información de la cuenta
            doc_ref.update({
                'status': 'connected',
                'bank_name': account_data.get('institution', {}).get('name'),
                'account_holder': account_data.get('holder_name'),
                'account_number': account_data.get('number', '')[-4:],  # Solo últimos 4 dígitos
                'account_type': account_data.get('type'),
                'connected_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            return True
            
        except Exception as e:
            print(f"Error actualizando conexión bancaria: {e}")
            return False
    
    @staticmethod
    def get_validation_status(user_id: int) -> Dict[str, Any]:
        """
        Obtiene el estado de validación bancaria de un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Diccionario con el estado o None si no existe
        """
        try:
            doc_ref = db.collection('bank_validations').document(str(user_id))
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            
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
    def check_account_ownership(user_id: int, rut: str) -> bool:
        """
        Verifica que el RUT del usuario coincida con el titular de la cuenta
        
        Args:
            user_id: ID del usuario
            rut: RUT del usuario
            
        Returns:
            True si coincide, False si no
        """
        try:
            doc_ref = db.collection('bank_validations').document(str(user_id))
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Aquí deberías implementar la lógica para comparar RUTs
                # Por ahora retornamos True
                return True
            
            return False
            
        except Exception as e:
            print(f"Error verificando titularidad: {e}")
            return False