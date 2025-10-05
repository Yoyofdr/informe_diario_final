"""
Vistas para el sistema de suscripciones y pagos
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json
import logging
import uuid

from alerts.models import Plan, Subscription, Payment, Organization
from alerts.services.flow_service import flow_service

logger = logging.getLogger(__name__)


def pricing_page(request):
    """Página de precios con los planes disponibles"""
    plans = Plan.objects.filter(is_active=True).order_by('price')
    
    # Planes predefinidos
    individual_plan = plans.filter(plan_type='individual').first()
    organization_plan = plans.filter(plan_type='organizacion').first()
    
    context = {
        'individual_plan': individual_plan,
        'organization_plan': organization_plan,
        'user_has_subscription': request.user.is_authenticated and hasattr(request.user, 'subscription'),
    }
    
    return render(request, 'alerts/pricing_simple.html', context)


@login_required
def start_trial(request, plan_slug):
    """Inicia el período de prueba de 14 días"""
    
    # Verificar si ya tiene suscripción
    if hasattr(request.user, 'subscription'):
        messages.warning(request, "Ya tienes una suscripción activa.")
        return redirect('alerts:subscription_dashboard')
    
    # Obtener el plan
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)
    
    # Crear suscripción en estado trial
    subscription = Subscription.objects.create(
        user=request.user,
        plan=plan,
        status='trial',
        trial_end=timezone.now() + timedelta(days=7)
    )
    
    # Si es plan organización, crear la organización
    if plan.plan_type == 'organizacion' and 'organization_name' in request.POST:
        Organization.objects.create(
            name=request.POST.get('organization_name'),
            rut=request.POST.get('organization_rut', ''),
            subscription=subscription,
            owner=request.user,
            billing_email=request.user.email,
            billing_address=request.POST.get('billing_address', ''),
            phone=request.POST.get('phone', '')
        )
    
    messages.success(request, f"¡Bienvenido! Tu período de prueba de 7 días ha comenzado. Debes agregar un método de pago antes de que termine.")
    
    # Redirigir a agregar método de pago
    return redirect('alerts:add_payment_method')


@login_required
def add_payment_method(request):
    """Página para agregar método de pago"""
    
    # Verificar que tenga suscripción
    if not hasattr(request.user, 'subscription'):
        messages.error(request, "No tienes una suscripción activa.")
        return redirect('alerts:pricing')
    
    subscription = request.user.subscription
    
    if request.method == 'POST':
        # Crear orden de pago en Flow para validar tarjeta
        # Usamos un monto de $1 que será devuelto
        commerce_order = f"VALIDATE_{subscription.subscription_id}"
        
        try:
            # URLs de callback
            url_confirmation = request.build_absolute_uri(reverse('subscription:flow_webhook'))
            url_return = request.build_absolute_uri(reverse('subscription:payment_success'))
            
            # Crear pago de validación en Flow
            flow_response = flow_service.create_payment(
                amount=1,  # $1 CLP para validación
                email=request.user.email,
                subject="Validación de método de pago - Informe Diario Chile",
                commerceOrder=commerce_order,
                urlConfirmation=url_confirmation,
                urlReturn=url_return,
                optional={
                    'subscription_id': str(subscription.subscription_id),
                    'validation': 'true'
                }
            )
            
            # Guardar payment pendiente
            Payment.objects.create(
                subscription=subscription,
                user=request.user,
                plan=subscription.plan,
                amount=1,
                status='pending',
                flow_token=flow_response.get('token'),
                description="Validación de método de pago"
            )
            
            # Redirigir a Flow para que el usuario ingrese su tarjeta
            return redirect(flow_response['url'] + "?token=" + flow_response['token'])
            
        except Exception as e:
            logger.error(f"Error creating Flow payment: {str(e)}")
            messages.error(request, "Error al procesar el pago. Por favor intenta nuevamente.")
    
    context = {
        'subscription': subscription,
        'days_left': subscription.days_until_trial_end,
    }
    
    return render(request, 'alerts/add_payment_method.html', context)


@login_required
def subscription_dashboard(request):
    """Dashboard de la suscripción del usuario"""
    
    if not hasattr(request.user, 'subscription'):
        return redirect('alerts:pricing')
    
    subscription = request.user.subscription
    
    # Si es organización, obtener miembros
    organization = None
    if hasattr(subscription, 'organization'):
        organization = subscription.organization
    
    # Obtener pagos recientes
    recent_payments = Payment.objects.filter(
        subscription=subscription,
        status='completed'
    ).order_by('-created_at')[:5]
    
    context = {
        'subscription': subscription,
        'organization': organization,
        'recent_payments': recent_payments,
        'can_cancel': subscription.status in ['trial', 'active'],
    }
    
    return render(request, 'alerts/subscription_dashboard.html', context)


@login_required
@require_POST
def cancel_subscription(request):
    """Cancela la suscripción del usuario"""
    
    if not hasattr(request.user, 'subscription'):
        return JsonResponse({'error': 'No subscription found'}, status=404)
    
    subscription = request.user.subscription
    
    try:
        # Si tiene suscripción en Flow, cancelarla
        if subscription.flow_subscription_id:
            flow_service.cancel_subscription(subscription.flow_subscription_id)
        
        # Actualizar estado local
        subscription.cancel()
        
        messages.success(request, "Tu suscripción ha sido cancelada. Tendrás acceso hasta el final del período actual.")
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return JsonResponse({'error': 'Error al cancelar suscripción'}, status=500)


@csrf_exempt
@require_POST
def flow_webhook(request):
    """
    Webhook para recibir notificaciones de Flow
    Flow envía un POST con el token del pago
    """
    
    try:
        # Flow envía el token en el body
        token = request.POST.get('token')
        
        if not token:
            logger.error("Flow webhook received without token")
            return HttpResponse(status=400)
        
        # Verificar que el token es válido
        if not flow_service.verify_webhook(token):
            logger.error(f"Invalid Flow webhook token: {token}")
            return HttpResponse(status=400)
        
        # Obtener estado del pago
        payment_status = flow_service.get_payment_status(token)
        
        # Buscar el pago en nuestra BD
        payment = Payment.objects.filter(flow_token=token).first()
        
        if not payment:
            logger.error(f"Payment not found for token: {token}")
            return HttpResponse(status=404)
        
        # Actualizar estado según respuesta de Flow
        flow_status = payment_status.get('status')
        
        if flow_status == 2:  # Pagado
            payment.mark_as_paid()
            
            # Si es validación de tarjeta, marcar como agregada
            if payment.amount == 1 and 'validation' in payment.description.lower():
                subscription = payment.subscription
                subscription.payment_method_added = True
                
                # Si la suscripción está pendiente, ACTIVAR TRIAL AHORA
                if subscription.status == 'pending':
                    subscription.status = 'trial'
                    subscription.trial_start = timezone.now()
                    subscription.trial_end = timezone.now() + timedelta(days=7)
                    subscription.current_period_start = timezone.now()
                    subscription.current_period_end = timezone.now() + timedelta(days=7)
                    logger.info(f"Trial activado para {subscription.user.email} - Termina: {subscription.trial_end}")
                
                subscription.save()
            
            # Si es pago regular, actualizar fechas de suscripción
            elif payment.amount == payment.plan.price:
                subscription = payment.subscription
                subscription.last_payment_date = timezone.now()
                subscription.current_period_end = timezone.now() + timedelta(days=30)
                subscription.next_payment_date = subscription.current_period_end
                subscription.status = 'active'
                subscription.save()
        
        elif flow_status == 3:  # Rechazado
            payment.status = 'failed'
            payment.failure_reason = payment_status.get('paymentData', {}).get('message', 'Pago rechazado')
            payment.save()
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error processing Flow webhook: {str(e)}")
        return HttpResponse(status=500)


@login_required
def payment_success(request):
    """Página de éxito después del pago"""
    
    # Flow redirige aquí con el token
    token = request.GET.get('token')
    
    if token:
        # Verificar estado del pago
        try:
            payment_status = flow_service.get_payment_status(token)
            
            if payment_status.get('status') == 2:  # Pagado
                messages.success(request, "¡Pago procesado exitosamente!")
            else:
                messages.warning(request, "El pago está siendo procesado. Te notificaremos cuando esté completo.")
        except:
            pass
    
    return redirect('alerts:subscription_dashboard')


@login_required
def payment_failure(request):
    """Página de fallo en el pago"""
    messages.error(request, "El pago no pudo ser procesado. Por favor intenta con otro método de pago.")
    return redirect('alerts:add_payment_method')