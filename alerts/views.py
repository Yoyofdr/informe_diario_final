from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
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
from .enviar_informe_bienvenida import enviar_informe_bienvenida
from django.db import transaction

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
            auth_login(request, user)
            
            # Enviar informe de bienvenida
            try:
                nombre_completo = f"{user.first_name} {user.last_name}".strip()
                if not nombre_completo:
                    nombre_completo = user.username
                
                enviar_informe_bienvenida(user.email, nombre_completo)
                messages.success(request, 'Te hemos enviado el informe del Diario Oficial de hoy por email.')
            except Exception as e:
                print(f"Error enviando informe de bienvenida: {e}")
                # No mostrar error al usuario para no afectar la experiencia de registro
            
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
    return render(request, 'alerts/dashboard_chennai.html', {
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
                
                # Enviar informe de bienvenida
                try:
                    enviar_informe_bienvenida(destinatario.email, destinatario.nombre)
                    mensaje = f"Registro exitoso. Te hemos agregado a la lista de destinatarios y enviado el informe de hoy por email."
                except Exception as e:
                    print(f"Error enviando informe de bienvenida: {e}")
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
        return render(request, 'panel_organizacion_chennai.html')
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
                
                # Enviar informe de bienvenida al nuevo destinatario
                try:
                    enviar_informe_bienvenida(destinatario.email, destinatario.nombre)
                    messages.success(request, f"Destinatario {form.cleaned_data['email']} agregado y se le envió el informe de hoy.")
                except Exception as e:
                    print(f"Error enviando informe de bienvenida: {e}")
                    messages.success(request, f"Destinatario {form.cleaned_data['email']} agregado.")
                
                form = DestinatarioForm(organizacion=organizacion)
            # else:
            #     messages.error(request, 'Por favor, corrige los errores del formulario.')
        elif 'eliminar' in request.POST:
            dest_id = request.POST.get('dest_id')
            Destinatario.objects.filter(id=dest_id, organizacion=organizacion).delete()
            messages.success(request, "Destinatario eliminado.")
    destinatarios = Destinatario.objects.select_related('organizacion').filter(organizacion=organizacion)
    return render(request, 'panel_organizacion_chennai.html', {
        'organizacion': organizacion,
        'destinatarios': destinatarios,
        'dominio': dominio,
        'form': form
    })

def registro_empresa_admin(request):
    if request.method == 'POST':
        form = RegistroEmpresaAdminForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            email_dominio = email.split('@')[1]
            
            # Verificar duplicados ANTES de crear
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con ese email.')
                return render(request, 'alerts/registro_empresa_admin.html', {'form': form})
            
            if Organizacion.objects.filter(dominio=email_dominio).exists():
                messages.error(request, 'Ya existe una organización con ese dominio.')
                return render(request, 'alerts/registro_empresa_admin.html', {'form': form})
            
            try:
                with transaction.atomic():
                    # Crear usuario
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=form.cleaned_data['password1'],
                        first_name=form.cleaned_data['nombre'],
                        last_name=form.cleaned_data['apellido']
                    )
                    
                    # Crear organización
                    org = Organizacion.objects.create(
                        nombre=form.cleaned_data['nombre_empresa'],
                        dominio=email_dominio,
                        admin=user
                    )
                    
                    # IMPORTANTE: Agregar como destinatario
                    Destinatario.objects.create(
                        nombre=f"{user.first_name} {user.last_name}",
                        email=email,
                        organizacion=org
                    )
                    
                    # Enviar informe de bienvenida dentro de la transacción
                    try:
                        nombre_completo = f"{user.first_name} {user.last_name}".strip()
                        enviar_informe_bienvenida(user.email, nombre_completo)
                    except Exception as e:
                        print(f"Error enviando informe de bienvenida: {e}")
                
                # Email de confirmación (fuera de la transacción)
                send_mail(
                    subject='Bienvenido a Informe Diario',
                    message=f'Hola {user.first_name},\n\nTu cuenta ha sido creada exitosamente.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True
                )
                
                messages.success(request, 'Registro exitoso. Te hemos enviado el informe del Diario Oficial de hoy.')
                return render(request, 'alerts/registro_exitoso.html', {'empresa': org})
                
            except Exception as e:
                messages.error(request, f'Error durante el registro: {str(e)}')
                return render(request, 'alerts/registro_empresa_admin.html', {'form': form})
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
            return render(request, 'registration/login_fixed.html')
        except MultipleObjectsReturned:
            print(f"[LOGIN] ERROR: Hay múltiples usuarios con el email: {email}")
            messages.error(request, "Error: Hay más de un usuario registrado con este email. Por favor contacta a soporte.")
            return render(request, 'registration/login_fixed.html')
        user_auth = authenticate(request, username=user.username, password=password)
        print(f"[LOGIN] Resultado authenticate: {user_auth}")
        if user_auth is not None and user_auth.is_active:
            auth_login(request, user_auth)
            print("[LOGIN] Login exitoso, redirigiendo a dashboard")
            return redirect('alerts:dashboard')
        else:
            print(f"[LOGIN] Falló la autenticación para usuario: {user.username} (email: {user.email})")
            messages.error(request, "Email o contraseña incorrectos.")
            return render(request, 'registration/login_fixed.html')
    return render(request, 'registration/login_fixed.html')

def landing_explicativa(request):
    """
    Landing explicativa del producto, con botón para probar gratis.
    """
    return render(request, 'alerts/landing_explicativa_chennai.html')

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
            # Extraer dominio del email
            dominio = email.split('@')[1].lower().strip()
            # No hay destinatarios adicionales en este formulario - solo el admin
            
            # Verificar email duplicado
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con ese email.')
                return render(request, 'alerts/registro_prueba_chennai.html', {'form': form})
            
            # Si todo está OK, proceder con el registro
            try:
                with transaction.atomic():
                    password = form.cleaned_data['password1']
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=nombre,
                        last_name=apellido
                    )
                    
                    # Buscar si ya existe una organización para este dominio
                    org = Organizacion.objects.filter(dominio=dominio).first()
                    if not org:
                        # Crear nueva organización si no existe
                        org = Organizacion.objects.create(
                            nombre=empresa_nombre,
                            dominio=dominio,
                            admin=user
                        )
                    # Si ya existe, simplemente usar la organización existente
                    # El usuario se agregará como destinatario más abajo
                    
                    # IMPORTANTE: Agregar al admin como destinatario principal
                    admin_destinatario = Destinatario.objects.create(
                        nombre=f"{nombre} {apellido}",
                        email=email,
                        organizacion=org
                    )
                    
                    # Enviar informe de bienvenida al admin
                    try:
                        nombre_completo = f"{nombre} {apellido}".strip()
                        enviar_informe_bienvenida(email, nombre_completo)
                    except Exception as e:
                        print(f"Error enviando informe de bienvenida al admin: {e}")
                    
                    # No hay destinatarios adicionales en este formulario simplificado
                    
                    # Enviar email de confirmación DESPUÉS de que todo esté creado
                    send_mail(
                        subject='Bienvenido a Informe Diario',
                        message=f'Hola {nombre},\n\nTu cuenta ha sido creada exitosamente.\n\nEmail: {email}\n\nYa puedes iniciar sesión en la plataforma.\n\n¡Bienvenido!',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    
                    messages.success(request, 'Registro exitoso. Te hemos enviado el informe del Diario Oficial de hoy por email. Ya puedes iniciar sesión y usar la plataforma gratis.')
                    # Redirigir al formulario para mostrar el popup de éxito
                    return redirect('alerts:registro_prueba')
                
            except Exception as e:
                # Si algo falla, eliminar el usuario creado
                if 'user' in locals():
                    user.delete()
                messages.error(request, f'Error durante el registro: {str(e)}')
                return render(request, 'alerts/registro_prueba_chennai.html', {'form': form})
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = RegistroPruebaForm()
    return render(request, 'alerts/registro_prueba_chennai.html', {'form': form})

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
    return render(request, 'alerts/historial_informes_chennai.html', {'informes': informes})

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

def logout_view(request):
    """Vista personalizada de logout que acepta GET requests"""
    print(f"[LOGOUT] Usuario {request.user} cerrando sesión")
    auth_logout(request)
    print("[LOGOUT] Sesión cerrada, redirigiendo a landing")
    return redirect('/') 