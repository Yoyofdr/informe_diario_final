"""
Servicio de integración con Flow para procesamiento de pagos
"""
import hashlib
import hmac
import json
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.urls import reverse
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FlowService:
    """
    Servicio para integración con Flow.cl
    Documentación: https://www.flow.cl/docs/api.html
    """
    
    # URLs de Flow
    SANDBOX_URL = "https://sandbox.flow.cl/api"
    PRODUCTION_URL = "https://www.flow.cl/api"
    
    def __init__(self):
        """Inicializa el servicio con las credenciales de Flow"""
        self.api_key = getattr(settings, 'FLOW_API_KEY', '')
        self.secret_key = getattr(settings, 'FLOW_SECRET_KEY', '')
        self.is_sandbox = getattr(settings, 'FLOW_SANDBOX', True)
        self.base_url = self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL
        
        if not self.api_key or not self.secret_key:
            logger.warning("Flow credentials not configured. Please set FLOW_API_KEY and FLOW_SECRET_KEY in settings.")
    
    def _sign_params(self, params: Dict) -> str:
        """
        Firma los parámetros según la documentación de Flow
        
        Args:
            params: Diccionario con los parámetros a firmar
            
        Returns:
            str: Firma HMAC SHA256 en hexadecimal
        """
        # Ordenar parámetros alfabéticamente
        sorted_params = sorted(params.items())
        
        # Crear string para firmar
        to_sign = '&'.join([f"{key}={value}" for key, value in sorted_params])
        
        # Generar firma HMAC SHA256
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_request(self, endpoint: str, params: Dict, method: str = 'POST') -> Dict:
        """
        Realiza una petición a la API de Flow
        
        Args:
            endpoint: Endpoint de la API
            params: Parámetros de la petición
            method: Método HTTP (POST o GET)
            
        Returns:
            Dict: Respuesta de la API
        """
        # Agregar apiKey a los parámetros
        params['apiKey'] = self.api_key
        
        # Firmar parámetros
        params['s'] = self._sign_params(params)
        
        # URL completa
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == 'POST':
                response = requests.post(url, data=params, timeout=30)
            else:
                response = requests.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Flow API error: {str(e)}")
            raise Exception(f"Error comunicándose con Flow: {str(e)}")
    
    def create_payment(self, amount: int, email: str, subject: str, 
                      commerceOrder: str, urlConfirmation: str, 
                      urlReturn: str, optional: Dict = None) -> Dict:
        """
        Crea una orden de pago en Flow
        
        Args:
            amount: Monto en CLP
            email: Email del pagador
            subject: Descripción del pago
            commerceOrder: ID único de la orden
            urlConfirmation: URL de confirmación (webhook)
            urlReturn: URL de retorno después del pago
            optional: Datos opcionales adicionales
            
        Returns:
            Dict: Respuesta con URL de pago y token
        """
        params = {
            'commerceOrder': commerceOrder,
            'subject': subject,
            'amount': amount,
            'email': email,
            'urlConfirmation': urlConfirmation,
            'urlReturn': urlReturn,
        }
        
        # Agregar parámetros opcionales si existen
        if optional:
            params['optional'] = json.dumps(optional)
        
        response = self._make_request('payment/create', params)
        
        # La respuesta incluye:
        # - url: URL donde redirigir al usuario para pagar
        # - token: Token único del pago
        # - flowOrder: Número de orden en Flow
        
        return response
    
    def create_subscription(self, plan_id: str, customer_id: str, 
                          subscription_start: str = None) -> Dict:
        """
        Crea una suscripción recurrente en Flow
        
        Args:
            plan_id: ID del plan en Flow
            customer_id: ID del cliente en Flow
            subscription_start: Fecha de inicio (opcional)
            
        Returns:
            Dict: Información de la suscripción creada
        """
        params = {
            'planId': plan_id,
            'customerId': customer_id,
        }
        
        if subscription_start:
            params['subscription_start'] = subscription_start
        
        return self._make_request('subscription/create', params)
    
    def create_customer(self, email: str, name: str, external_id: str = None) -> Dict:
        """
        Crea un cliente en Flow para suscripciones
        
        Args:
            email: Email del cliente
            name: Nombre del cliente
            external_id: ID externo (opcional)
            
        Returns:
            Dict: Información del cliente creado
        """
        params = {
            'email': email,
            'name': name,
        }
        
        if external_id:
            params['externalId'] = external_id
        
        return self._make_request('customer/create', params)
    
    def get_payment_status(self, token: str) -> Dict:
        """
        Obtiene el estado de un pago
        
        Args:
            token: Token del pago
            
        Returns:
            Dict: Estado del pago
        """
        params = {'token': token}
        return self._make_request('payment/getStatus', params, method='GET')
    
    def cancel_subscription(self, subscription_id: str) -> Dict:
        """
        Cancela una suscripción
        
        Args:
            subscription_id: ID de la suscripción en Flow
            
        Returns:
            Dict: Confirmación de cancelación
        """
        params = {'subscriptionId': subscription_id}
        return self._make_request('subscription/cancel', params)
    
    def verify_webhook(self, token: str) -> bool:
        """
        Verifica que un webhook viene de Flow
        
        Args:
            token: Token recibido en el webhook
            
        Returns:
            bool: True si es válido
        """
        try:
            # Obtener estado del pago con el token
            status = self.get_payment_status(token)
            return status is not None
        except:
            return False
    
    def create_plan(self, name: str, amount: int, interval: int = 1, 
                   interval_count: int = 1, trial_period_days: int = 14) -> Dict:
        """
        Crea un plan de suscripción en Flow
        
        Args:
            name: Nombre del plan
            amount: Monto en CLP
            interval: 1=Día, 2=Semana, 3=Mes, 4=Año
            interval_count: Cantidad de intervalos
            trial_period_days: Días de prueba
            
        Returns:
            Dict: Información del plan creado
        """
        params = {
            'name': name,
            'amount': amount,
            'interval': interval,  # 3 para mensual
            'interval_count': interval_count,  # 1 para cada mes
            'trial_period_days': trial_period_days,
        }
        
        return self._make_request('plans/create', params)


# Instancia singleton del servicio
flow_service = FlowService()