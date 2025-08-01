"""
Vistas para la integración con Fintoc
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
import json
import os
# Usar la versión simplificada para desarrollo
try:
    from .fintoc_integration_simple import FintocIntegrationSimple as FintocIntegration
except ImportError:
    from .fintoc_integration import FintocIntegration
from .models import Organizacion


@login_required
def iniciar_validacion_bancaria(request):
    """
    Inicia el proceso de validación bancaria con Fintoc
    """
    if request.method == 'GET':
        # Verificar si el usuario ya tiene una validación
        validation_status = FintocIntegration.get_validation_status(request.user.id)
        
        if validation_status.get('status') == 'connected':
            messages.info(request, 'Ya tienes una cuenta bancaria conectada.')
            return redirect('alerts:dashboard')
        
        # Crear link token
        link_token = FintocIntegration.create_link_token(
            user_email=request.user.email,
            user_id=request.user.id
        )
        
        if link_token:
            context = {
                'link_token': link_token,
                'public_key': os.environ.get('FINTOC_PUBLIC_KEY'),
                'user_email': request.user.email
            }
            return render(request, 'alerts/validacion_bancaria.html', context)
        else:
            messages.error(request, 'Error al iniciar la validación bancaria. Por favor intenta más tarde.')
            return redirect('alerts:dashboard')
    
    return redirect('alerts:dashboard')


@login_required
def estado_validacion_bancaria(request):
    """
    Endpoint AJAX para verificar el estado de la validación bancaria
    """
    validation_status = FintocIntegration.get_validation_status(request.user.id)
    return JsonResponse(validation_status)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_fintoc(request):
    """
    Webhook para recibir notificaciones de Fintoc
    """
    try:
        # Parsear el payload
        payload = json.loads(request.body)
        event_type = payload.get('type')
        
        if event_type == 'link.credentials_changed':
            # El usuario completó la conexión
            link_data = payload.get('data', {})
            link_token = link_data.get('id')
            
            # Obtener información de la cuenta
            # Aquí deberías usar el API de Fintoc para obtener los detalles
            # Por ahora simulamos los datos
            account_data = {
                'institution': {'name': link_data.get('institution', 'Banco')},
                'holder_name': link_data.get('holder_name', ''),
                'number': link_data.get('account_number', '****'),
                'type': 'checking'
            }
            
            # Buscar el usuario por el link_token en Firestore
            # Aquí deberías implementar la búsqueda real
            user_id = 1  # Placeholder
            
            # Actualizar el estado
            FintocIntegration.update_bank_connection(
                user_id=user_id,
                link_token=link_token,
                account_data=account_data
            )
        
        return HttpResponse(status=200)
        
    except Exception as e:
        print(f"Error en webhook Fintoc: {e}")
        return HttpResponse(status=400)


@login_required
def desconectar_cuenta_bancaria(request):
    """
    Permite al usuario desconectar su cuenta bancaria
    """
    if request.method == 'POST':
        try:
            # Desconectar la cuenta
            FintocIntegration.disconnect_account(request.user.id)
            
            messages.success(request, 'Cuenta bancaria desconectada exitosamente.')
        except Exception as e:
            messages.error(request, 'Error al desconectar la cuenta bancaria.')
    
    return redirect('alerts:dashboard')