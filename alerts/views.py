from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomUserCreationForm, DestinatarioForm, RegistroEmpresaAdminForm, EmailAuthenticationForm, RegistroPruebaForm
from .models import Empresa, PerfilUsuario, SuscripcionLanding, Organizacion, Destinatario, InformeEnviado
from collections import defaultdict
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
import json
from datetime import timedelta
from django.contrib.auth.models import User
import os
import requests
import urllib.parse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from alerts.utils.db_optimizations import optimize_empresa_queries, optimize_hecho_esencial_queries, optimize_metrics_queries, QueryOptimizer

@login_required
def suscripcion_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            empresa_id = data.get('empresa_id')
            checked = data.get('checked')

            empresa = Empresa.objects.get(id=empresa_id)
            perfil = request.user.perfil

            if checked:
                perfil.suscripciones.add(empresa)
            else:
                perfil.suscripciones.remove(empresa)

            return JsonResponse({'status': 'ok', 'message': 'Suscripción actualizada.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
def actualizar_suscripciones(request):
    """
    Procesa la actualización de las suscripciones de un usuario.
    Solo responde a métodos POST.
    """
    if request.method == 'POST':
        suscripciones_ids = request.POST.getlist('suscripciones')
        perfil = request.user.perfil
        perfil.suscripciones.set(suscripciones_ids)
    
    return redirect('alerts:dashboard')


def register(request):
    """
    Gestiona el registro de nuevos usuarios.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Crear organización automáticamente para el nuevo usuario
            # Extraer dominio del email
            email_domain = user.email.split('@')[1] if '@' in user.email else 'personal.cl'
            
            # Crear nombre de organización basado en el nombre del usuario o email
            if user.first_name and user.last_name:
                org_name = f"{user.first_name} {user.last_name}"
            elif user.first_name:
                org_name = user.first_name
            else:
                org_name = user.email.split('@')[0]
            
            # Crear la organización
            organizacion = Organizacion.objects.create(
                nombre=org_name,
                dominio=email_domain,
                admin=user,
                plan='gratis',
                suscripcion_activa=True  # Activar automáticamente para usuarios nuevos
            )
            
            # Agregar al usuario como destinatario de su propia organización
            Destinatario.objects.create(
                nombre=user.get_full_name() or user.username,
                email=user.email,
                organizacion=organizacion
            )
            
            auth_login(request, user)
            return redirect('alerts:dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard(request):
    """
    Dashboard personalizado para el cliente.
    Muestra nombre, estado de prueba/suscripción, acceso a gestión de destinatarios y resumen de destinatarios.
    """
    user = request.user
    # Buscar organización donde el usuario es admin
    try:
        organizacion = Organizacion.objects.select_related('admin').get(admin=user)
    except Organizacion.DoesNotExist:
        organizacion = None
    destinatarios = Destinatario.objects.select_related('organizacion').filter(organizacion=organizacion) if organizacion else []
    # Estado de acceso (ahora siempre gratuito)
    if organizacion:
        estado = "Acceso gratuito activo"
    else:
        estado = "Sin organización asociada"
    return render(request, 'alerts/dashboard.html', {
        'user': user,
        'organizacion': organizacion,
        'destinatarios': destinatarios,
        'estado': estado
    })


def landing(request):
    """
    Vista pública para agregar destinatarios al sistema.
    """
    mensaje = None
    if request.method == 'POST':
        form = DestinatarioForm(request.POST)
        if form.is_valid():
            destinatario = form.save(commit=False)
            # Combinar nombre y apellido
            nombre = form.cleaned_data.get('nombre', '')
            apellido = form.cleaned_data.get('apellido', '')
            destinatario.nombre = f"{nombre} {apellido}".strip()
            
            # Asignar organización por defecto (la primera que exista)
            # En un caso real deberías tener una lógica específica para esto
            org = Organizacion.objects.first()
            if org:
                destinatario.organizacion = org
                destinatario.save()
                mensaje = f"Registro exitoso. Te hemos agregado a la lista de destinatarios."
                messages.success(request, mensaje)
                form = DestinatarioForm()  # Limpiar el form
            else:
                messages.error(request, "No hay organizaciones disponibles. Contacta al administrador.")
        else:
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
    else:
        form = DestinatarioForm()
    return render(request, 'landing.html', {'form': form})

@login_required
def panel_organizacion(request):
    """
    Panel para que el admin de la organización gestione los destinatarios.
    """
    try:
        organizacion = Organizacion.objects.select_related('admin').get(admin=request.user)
    except Organizacion.DoesNotExist:
        messages.error(request, 'No tienes una organización asociada.')
        return render(request, 'panel_organizacion.html')
    # Eliminar validación de pago/suscripción
    dominio = organizacion.dominio.lower().strip()
    form = DestinatarioForm(organizacion=organizacion)
    if request.method == 'POST':
        if 'agregar' in request.POST:
            form = DestinatarioForm(request.POST, organizacion=organizacion)
            if form.is_valid():
                destinatario = form.save(commit=False)
                # Combinar nombre y apellido
                nombre = form.cleaned_data.get('nombre', '')
                apellido = form.cleaned_data.get('apellido', '')
                destinatario.nombre = f"{nombre} {apellido}".strip()
                destinatario.organizacion = organizacion
                destinatario.save()
                messages.success(request, f"Destinatario {form.cleaned_data['email']} agregado.")
                form = DestinatarioForm(organizacion=organizacion)
            # else:
            #     messages.error(request, 'Por favor, corrige los errores del formulario.')
        elif 'eliminar' in request.POST:
            dest_id = request.POST.get('dest_id')
            Destinatario.objects.filter(id=dest_id, organizacion=organizacion).delete()
            messages.success(request, "Destinatario eliminado.")
    destinatarios = Destinatario.objects.select_related('organizacion').filter(organizacion=organizacion)
    return render(request, 'panel_organizacion.html', {
        'organizacion': organizacion,
        'destinatarios': destinatarios,
        'dominio': dominio,
        'form': form
    })

def registro_empresa_admin(request):
    if request.method == 'POST':
        form = RegistroEmpresaAdminForm(request.POST)
        if form.is_valid():
            # Siempre guardar el email como username para compatibilidad, pero el login será solo por email
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data['nombre'],
                last_name=form.cleaned_data['apellido']
            )
            # Generar dominio basado en el email del administrador
            email_dominio = form.cleaned_data['email'].split('@')[1]
            org = Organizacion.objects.create(
                nombre=form.cleaned_data['nombre_empresa'],
                dominio=email_dominio,
                admin=user
            )
            messages.success(request, 'Registro exitoso. Ahora puedes iniciar sesión.')
            return render(request, 'alerts/registro_exitoso.html', {'empresa': org})
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = RegistroEmpresaAdminForm()
    return render(request, 'alerts/registro_empresa_admin.html', {'form': form})

def login_email(request):
    from django.contrib.auth import authenticate
    from django.contrib.auth import login as auth_login
    from django.core.exceptions import MultipleObjectsReturned
    mensaje = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        print(f"[LOGIN] Intentando login con email: {email}")
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(email=email)
            print(f"[LOGIN] Usuario encontrado: {user} (activo: {user.is_active}, username: {user.username})")
        except User.DoesNotExist:
            print(f"[LOGIN] No existe usuario con email: {email}")
            messages.error(request, "No existe un usuario con ese email.")
            return render(request, 'registration/login.html')
        except MultipleObjectsReturned:
            print(f"[LOGIN] ERROR: Hay múltiples usuarios con el email: {email}")
            messages.error(request, "Error: Hay más de un usuario registrado con este email. Por favor contacta a soporte.")
            return render(request, 'registration/login.html')
        user_auth = authenticate(request, username=user.username, password=password)
        print(f"[LOGIN] Resultado authenticate: {user_auth}")
        if user_auth is not None and user_auth.is_active:
            auth_login(request, user_auth)
            print("[LOGIN] Login exitoso, redirigiendo a dashboard")
            return redirect('alerts:dashboard')
        else:
            print(f"[LOGIN] Falló la autenticación para usuario: {user.username} (email: {user.email})")
            messages.error(request, "Email o contraseña incorrectos.")
            return render(request, 'registration/login.html')
    return render(request, 'registration/login.html')

def landing_explicativa(request):
    """
    Landing explicativa del producto, con botón para probar gratis.
    """
    return render(request, 'alerts/landing_explicativa.html')

def registro_prueba(request):
    mensaje = None
    if request.method == 'POST':
        form = RegistroPruebaForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            apellido = form.cleaned_data['apellido']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data['telefono']
            empresa_nombre = form.cleaned_data['empresa']
            dominio = form.cleaned_data['dominio'].lower().strip()
            destinatarios = form.cleaned_data['destinatarios']
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con ese email.')
                return render(request, 'alerts/registro_prueba.html', {'form': form})
            else:
                password = form.cleaned_data['password1']
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=nombre,
                    last_name=apellido
                )
                send_mail(
                    subject='Bienvenido a Informe Diario - Resumen Integrado',
                    message=f'Hola {nombre},\n\nTu cuenta ha sido creada exitosamente.\n\nEmail: {email}\n\nAhora recibirás diariamente un informe integrado con información de:\n• Diario Oficial: Normativas y avisos relevantes\n• CMF: Hechos esenciales del mercado financiero\n• SII: Circulares y resoluciones tributarias\n\nPuedes iniciar sesión aquí: http://localhost:8000/login/\n\n¡Bienvenido a Informe Diario!',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            if Organizacion.objects.filter(dominio=dominio).exists():
                messages.error(request, 'Ya existe una organización con ese dominio.')
            else:
                org = Organizacion.objects.create(
                    nombre=empresa_nombre,
                    dominio=dominio,
                    admin=user
                )
                for dest_email in destinatarios:
                    Destinatario.objects.create(
                        nombre=f"{nombre} {apellido}",  # Usar el nombre del admin como placeholder
                        email=dest_email,
                        organizacion=org
                    )
                messages.success(request, 'Registro exitoso. Ya puedes iniciar sesión y usar la plataforma gratis.')
                return render(request, 'alerts/registro_exitoso.html', {'empresa': org})
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = RegistroPruebaForm()
    return render(request, 'alerts/registro_prueba.html', {'form': form})

@login_required
def historial_informes(request):
    user = request.user
    if user.is_superuser:
        informes = QueryOptimizer.get_recent_informes()
    else:
        try:
            organizacion = Organizacion.objects.select_related('admin').get(admin=user)
            empresa = Empresa.objects.filter(nombre__iexact=organizacion.nombre).first()
            if empresa:
                informes = QueryOptimizer.get_recent_informes(empresa_id=empresa.id)
            else:
                informes = []
        except Organizacion.DoesNotExist:
            informes = []
    return render(request, 'alerts/historial_informes.html', {'informes': informes})

@user_passes_test(lambda u: u.is_superuser)
def admin_panel(request):
    from django.contrib.auth.models import User
    empresas = optimize_empresa_queries(Empresa.objects.all().order_by('nombre'))
    usuarios = User.objects.all().order_by('email')
    destinatarios = Destinatario.objects.select_related('organizacion').all().order_by('email')
    return render(request, 'alerts/admin_panel.html', {
        'empresas': empresas,
        'usuarios': usuarios,
        'destinatarios': destinatarios
    }) 