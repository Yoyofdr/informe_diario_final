"""
Middleware para verificar el estado de las suscripciones
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin


class SubscriptionMiddleware(MiddlewareMixin):
    """
    Middleware que verifica que los usuarios tengan una suscripción activa
    para acceder a ciertas partes del sistema
    """
    
    # URLs que requieren suscripción activa
    PROTECTED_PATHS = [
        '/alerts/dashboard/',
        '/alerts/historial-informes/',
        '/alerts/panel-organizacion/',
    ]
    
    # URLs siempre accesibles (sin necesidad de suscripción)
    PUBLIC_PATHS = [
        '/alerts/',
        '/alerts/registro/',
        '/alerts/login/',
        '/alerts/subscription/pricing/',
        '/alerts/subscription/start-trial/',
        '/alerts/subscription/add-payment-method/',
        '/alerts/subscription/flow/',
        '/alerts/subscription/payment/',
        '/admin/',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        """Procesa cada request para verificar suscripción"""
        
        # Si no está autenticado, no hacer nada (el login lo manejará)
        if not request.user.is_authenticated:
            return None
        
        # Si es superusuario, tiene acceso total
        if request.user.is_superuser:
            return None
        
        # Verificar si la URL requiere suscripción
        path = request.path
        requires_subscription = False
        
        for protected_path in self.PROTECTED_PATHS:
            if path.startswith(protected_path):
                requires_subscription = True
                break
        
        # Si no requiere suscripción, continuar
        if not requires_subscription:
            return None
        
        # Verificar si el usuario tiene suscripción
        if not hasattr(request.user, 'subscription'):
            # No tiene suscripción, redirigir a pricing
            messages.warning(
                request, 
                "Necesitas una suscripción activa para acceder a esta sección. "
                "Comienza tu prueba gratuita de 14 días."
            )
            return redirect('subscription:pricing')
        
        subscription = request.user.subscription
        
        # Verificar si la suscripción está activa
        if not subscription.is_active:
            # Suscripción expirada o cancelada
            if subscription.status == 'expired' or subscription.status == 'canceled':
                messages.error(
                    request,
                    "Tu suscripción ha expirado. Por favor, renueva tu plan para continuar."
                )
                return redirect('subscription:pricing')
            elif subscription.status == 'past_due':
                messages.warning(
                    request,
                    "Hay un problema con tu pago. Por favor, actualiza tu método de pago."
                )
                return redirect('subscription:add_payment_method')
        
        # Si está en trial y faltan pocos días, mostrar advertencia
        if subscription.is_trial:
            days_left = subscription.days_until_trial_end
            
            # Si no ha agregado método de pago y quedan pocos días
            if not subscription.payment_method_added:
                if days_left <= 3:
                    messages.warning(
                        request,
                        f"Tu período de prueba termina en {days_left} días. "
                        f"Agrega un método de pago para no perder el acceso."
                    )
                elif days_left <= 7:
                    messages.info(
                        request,
                        f"Te quedan {days_left} días de prueba. "
                        f"No olvides agregar tu método de pago."
                    )
        
        # Todo OK, continuar
        return None


class SubscriptionContextMiddleware(MiddlewareMixin):
    """
    Middleware que agrega información de suscripción al contexto
    """
    
    def process_template_response(self, request, response):
        """Agrega datos de suscripción al contexto de los templates"""
        
        if hasattr(response, 'context_data'):
            if request.user.is_authenticated:
                # Agregar info de suscripción al contexto
                if hasattr(request.user, 'subscription'):
                    subscription = request.user.subscription
                    response.context_data['user_subscription'] = subscription
                    response.context_data['subscription_active'] = subscription.is_active
                    response.context_data['subscription_trial'] = subscription.is_trial
                    response.context_data['subscription_days_left'] = subscription.days_until_trial_end
                else:
                    response.context_data['user_subscription'] = None
                    response.context_data['subscription_active'] = False
                    response.context_data['subscription_trial'] = False
                    response.context_data['subscription_days_left'] = 0
        
        return response