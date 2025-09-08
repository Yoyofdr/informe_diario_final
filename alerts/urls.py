from django.urls import path
from . import views
# from . import views_fintoc  # DESACTIVADO TEMPORALMENTE - Activar cuando se habiliten cuentas bancarias
from django.contrib.auth import views as auth_views
from .forms import CustomPasswordChangeForm

# Este es el namespace de la app, para llamar a las urls como 'alerts:dashboard'
app_name = 'alerts'

urlpatterns = [
    path('', views.landing_explicativa, name='landing_explicativa'),
    path('registro/', views.registro_prueba, name='registro_prueba'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_email, name='login'),
    # path('register/', views.register, name='register'),  # Desactivado - usar registro_prueba
    # path('landing/', views.landing, name='landing'),  # Desactivado - usar landing_explicativa
    path('actualizar_suscripciones/', views.actualizar_suscripciones, name='actualizar_suscripciones'),
    path('suscripcion_ajax/', views.suscripcion_ajax, name='suscripcion_ajax'),
    path('panel-organizacion/', views.panel_organizacion, name='panel_organizacion'),
    # path('registro/', views.registro_empresa_admin, name='registro_empresa_admin'),  # Desactivado - template no existe
    path('historial-informes/', views.historial_informes, name='historial_informes'),
    # Password reset URLs - TEMPORALMENTE DESACTIVADAS hasta que se creen los templates Chennai
    # path('password_reset/', auth_views.PasswordResetView.as_view(template_name='alerts/password_reset_form.html'), name='password_reset'),
    # path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='alerts/password_reset_done.html'), name='password_reset_done'),
    # path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='alerts/password_reset_confirm.html'), name='password_reset_confirm'),
    # path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='alerts/password_reset_complete.html'), name='password_reset_complete'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='alerts/password_change_form_chennai.html', form_class=CustomPasswordChangeForm), name='password_change'),
    # path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='alerts/password_change_done.html'), name='password_change_done'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),  # Panel de administración para superusuarios
    path('logout/', views.logout_view, name='logout'),
    path('editar-dias-prueba/<int:destinatario_id>/', views.editar_dias_prueba, name='editar_dias_prueba'),
    
    # Fintoc integration URLs - DESACTIVADAS TEMPORALMENTE
    # Descomentar estas líneas cuando se active la funcionalidad de cuentas bancarias
    # path('validacion-bancaria/', views_fintoc.iniciar_validacion_bancaria, name='validacion_bancaria'),
    # path('validacion-bancaria/estado/', views_fintoc.estado_validacion_bancaria, name='estado_validacion_bancaria'),
    # path('validacion-bancaria/desconectar/', views_fintoc.desconectar_cuenta_bancaria, name='desconectar_cuenta_bancaria'),
    # path('webhooks/fintoc/', views_fintoc.webhook_fintoc, name='webhook_fintoc'),
] 