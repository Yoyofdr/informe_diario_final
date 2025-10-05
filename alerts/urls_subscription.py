"""
URLs para el sistema de suscripciones
"""
from django.urls import path
from alerts import subscription_views

app_name = 'subscription'

urlpatterns = [
    # Páginas públicas
    path('pricing/', subscription_views.pricing_page, name='pricing'),
    
    # Gestión de suscripción (requiere login)
    path('start-trial/<slug:plan_slug>/', subscription_views.start_trial, name='start_trial'),
    path('add-payment-method/', subscription_views.add_payment_method, name='add_payment_method'),
    path('dashboard/', subscription_views.subscription_dashboard, name='dashboard'),
    path('cancel/', subscription_views.cancel_subscription, name='cancel'),
    
    # Callbacks de Flow
    path('flow/webhook/', subscription_views.flow_webhook, name='flow_webhook'),
    path('payment/success/', subscription_views.payment_success, name='payment_success'),
    path('payment/failure/', subscription_views.payment_failure, name='payment_failure'),
]