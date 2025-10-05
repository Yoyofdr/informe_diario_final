from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomUserCreationForm, DestinatarioForm, RegistroEmpresaAdminForm, EmailAuthenticationForm, RegistroPruebaForm
from .models import Empresa, PerfilUsuario, SuscripcionLanding, Organizacion, Destinatario, InformeEnviado
from collections import defaultdict
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
import json
from datetime import timedelta, datetime
from django.contrib.auth.models import User
import os
import requests
import urllib.parse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.db import models
from alerts.utils.db_optimizations import optimize_empresa_queries, optimize_hecho_esencial_queries, optimize_metrics_queries, QueryOptimizer
from .enviar_informe_bienvenida import enviar_informe_bienvenida
from .services.registro_service import handle_signup
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
                messages.success(request, 'Te hemos enviado el informe de hoy. Continuarás recibiéndolo diariamente a las 8:30 AM.')
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
    
    # Si es superusuario, redirigir al panel de administración
    if user.is_superuser:
        return redirect('alerts:admin_panel')
    
    # Obtener información de suscripción si existe
    subscription = None
    plan_name = "Sin plan"
    puede_agregar_usuarios = False
    try:
        from alerts.models import Subscription
        subscription = Subscription.objects.get(user=user)
        plan_name = subscription.plan.name
        puede_agregar_usuarios = (subscription.plan.plan_type == 'organizacion' and 
                                 subscription.status in ['active', 'trialing'])
    except Subscription.DoesNotExist:
        pass
    
    # Primero buscar si el usuario es admin de alguna organización
    try:
        organizacion = Organizacion.objects.select_related('admin').get(admin=user)
        es_admin = True
    except Organizacion.DoesNotExist:
        # Si no es admin, buscar si es destinatario de alguna organización
        try:
            destinatario = Destinatario.objects.select_related('organizacion').get(email=user.email)
            organizacion = destinatario.organizacion
            es_admin = False
        except Destinatario.DoesNotExist:
            organizacion = None
            es_admin = False
    
    destinatarios = Destinatario.objects.select_related('organizacion').filter(organizacion=organizacion) if organizacion else []
    
    # Estado de acceso (ahora siempre gratuito)
    if organizacion:
        if es_admin:
            estado = "Acceso gratuito activo (Administrador)"
        else:
            estado = "Acceso gratuito activo"
    else:
        estado = "Sin organización asociada"
    return render(request, 'alerts/dashboard_chennai.html', {
        'user': user,
        'organizacion': organizacion,
        'destinatarios': destinatarios,
        'estado': estado,
        'es_admin': es_admin if organizacion else False,
        'subscription': subscription,
        'plan_name': plan_name,
        'puede_agregar_usuarios': puede_agregar_usuarios
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
                    mensaje = f"Registro exitoso. Te hemos agregado a la lista de destinatarios y enviado el informe de hoy."
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
    Solo disponible para usuarios con Plan Organización activo.
    """
    # Verificar que el usuario tenga una suscripción activa del Plan Organización
    try:
        from alerts.models import Subscription
        subscription = Subscription.objects.get(user=request.user)
        if subscription.plan.plan_type != 'organizacion' or subscription.status not in ['active', 'trialing']:
            messages.error(request, 'Esta funcionalidad solo está disponible con el Plan Organización activo.')
            return redirect('subscription:pricing')
    except Subscription.DoesNotExist:
        messages.error(request, 'Necesitas contratar el Plan Organización para acceder a esta funcionalidad.')
        return redirect('subscription:pricing')
    
    try:
        organizacion = Organizacion.objects.select_related('admin').get(admin=request.user)
    except Organizacion.DoesNotExist:
        messages.error(request, 'No tienes una organización asociada.')
        return render(request, 'panel_organizacion_chennai.html')
    # Eliminar validación de pago/suscripción
    # Manejar el caso donde dominio puede ser None
    if organizacion.dominio:
        dominio = organizacion.dominio.lower().strip()
    else:
        # Si no hay dominio, usar el dominio del email del admin
        dominio = organizacion.admin.email.split('@')[1] if '@' in organizacion.admin.email else 'ejemplo.com'
    form = DestinatarioForm(organizacion=organizacion)
    if request.method == 'POST':
        if 'agregar' in request.POST:
            # Verificar límites del plan
            num_usuarios = Destinatario.objects.filter(organizacion=organizacion).count()
            # Plan Organización permite hasta 50 usuarios
            if num_usuarios >= 50:
                messages.error(request, 'Has alcanzado el límite de usuarios para tu plan (50 usuarios).')
                return redirect('alerts:panel_organizacion')
            
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
    
    # Calcular estadísticas de trials
    trials_activos = sum(1 for d in destinatarios if d.trial_activo() and not d.es_pagado)
    expiran_pronto = sum(1 for d in destinatarios if not d.es_pagado and 0 < d.dias_restantes_trial() <= 7)
    usuarios_pagados = sum(1 for d in destinatarios if d.es_pagado)
    trials_expirados = sum(1 for d in destinatarios if not d.es_pagado and d.dias_restantes_trial() == 0)
    
    return render(request, 'panel_organizacion_chennai.html', {
        'organizacion': organizacion,
        'destinatarios': destinatarios,
        'dominio': dominio,
        'form': form,
        'trials_activos': trials_activos,
        'expiran_pronto': expiran_pronto,
        'usuarios_pagados': usuarios_pagados,
        'trials_expirados': trials_expirados
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
                        telefono=telefono,  # Agregar el teléfono capturado del formulario
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
            return render(request, 'registration/login_chennai.html')
        except MultipleObjectsReturned:
            print(f"[LOGIN] ERROR: Hay múltiples usuarios con el email: {email}")
            messages.error(request, "Error: Hay más de un usuario registrado con este email. Por favor contacta a soporte.")
            return render(request, 'registration/login_chennai.html')
        user_auth = authenticate(request, username=user.username, password=password)
        print(f"[LOGIN] Resultado authenticate: {user_auth}")
        if user_auth is not None and user_auth.is_active:
            auth_login(request, user_auth)
            print("[LOGIN] Login exitoso, redirigiendo a dashboard")
            return redirect('alerts:dashboard')
        else:
            print(f"[LOGIN] Falló la autenticación para usuario: {user.username} (email: {user.email})")
            messages.error(request, "Email o contraseña incorrectos.")
            return render(request, 'registration/login_chennai.html')
    return render(request, 'registration/login_chennai.html')

def landing_explicativa(request):
    """
    Landing explicativa del producto, con botón para probar gratis.
    """
    return render(request, 'alerts/landing_explicativa_chennai.html')

def registro_prueba(request):
    print(f"[REGISTRO-TEST] Función registro_prueba iniciada - Method: {request.method}")
    import sys
    sys.stdout.flush()
    
    mensaje = None
    # Obtener el plan desde GET o POST
    plan_slug = request.GET.get('plan') or request.POST.get('plan', 'individual')
    print(f"[REGISTRO-TEST] Plan slug al inicio: {plan_slug}")
    sys.stdout.flush()
    
    if request.method == 'POST':
        print(f"[REGISTRO-TEST] POST recibido")
        sys.stdout.flush()
        form = RegistroPruebaForm(request.POST)
        print(f"[REGISTRO-TEST] Form creado, valid: {form.is_valid()}")
        sys.stdout.flush()
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            apellido = form.cleaned_data['apellido']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data['telefono']
            empresa_nombre = form.cleaned_data.get('empresa')
            rut_empresa = form.cleaned_data.get('rut_empresa')
            no_empresa = form.cleaned_data.get('no_empresa')
            
            # Verificar email duplicado
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con ese email.')
                return render(request, 'alerts/registro_prueba_chennai.html', {'form': form, 'plan': plan_slug})
            
            # Si todo está OK, proceder con el registro
            user = None  # Declarar user fuera del bloque
            try:
                with transaction.atomic():
                    password = form.cleaned_data['password1']
                    print(f"[REGISTRO] Creando usuario: {email}")
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=nombre,
                        last_name=apellido
                    )
                    print(f"[REGISTRO] Usuario creado con ID: {user.id}")
                    
                    # Usar el nuevo servicio de registro basado en RUT
                    org = handle_signup(
                        user=user,
                        rut=rut_empresa,
                        no_empresa=no_empresa,
                        nombre_empresa=empresa_nombre,
                        email=email,
                        nombre=nombre,
                        apellido=apellido,
                        telefono=telefono
                    )
                    
                    print(f"[REGISTRO] Organización: {org.nombre} (ID: {org.id}, Tipo: {org.tipo})")
                    
                    # Verificar que se guardó correctamente
                    user_check = User.objects.filter(id=user.id).exists()
                    org_check = Organizacion.objects.filter(id=org.id).exists()
                    
                    if not user_check or not org_check:
                        raise Exception("Error: Los datos no se guardaron correctamente")
                    
                    print(f"[REGISTRO] Verificación OK - Usuario: {user_check}, Organización: {org_check}")
                    
                # Fuera de la transacción - los datos ya deberían estar guardados
                print(f"[REGISTRO] Transacción completada exitosamente")
                print(f"[REGISTRO] Usuario disponible: {user is not None}")
                print(f"[REGISTRO] Email del usuario: {user.email if user else 'No user'}")
                
                # Forzar que los prints se muestren inmediatamente
                import sys
                sys.stdout.flush()
                
                # NUEVO: Crear suscripción trial si viene de la página de precios
                # plan_slug ya está definido arriba
                print(f"[REGISTRO] Plan slug recibido: {plan_slug}")
                sys.stdout.flush()
                
                try:
                    # Importar los modelos necesarios
                    from alerts.models import Plan, Subscription
                    
                    # DEPURACIÓN: Ver si llegamos aquí
                    print(f"[REGISTRO-DEBUG] ============ INICIO CREACIÓN SUSCRIPCIÓN ============")
                    print(f"[REGISTRO-DEBUG] Usuario: {user.email if user else 'NO USER'}")
                    print(f"[REGISTRO-DEBUG] Plan recibido: {plan_slug}")
                    sys.stdout.flush()
                    
                    # Obtener el plan seleccionado
                    plan = None
                    try:
                        plan = Plan.objects.get(slug=plan_slug, is_active=True)
                        print(f"[REGISTRO-DEBUG] Plan encontrado: {plan.name} (slug: {plan.slug})")
                    except Plan.DoesNotExist:
                        print(f"[REGISTRO-DEBUG] Plan {plan_slug} no existe, buscando individual por defecto")
                        # Si no existe el plan, usar el individual por defecto
                        plan = Plan.objects.filter(plan_type='individual', is_active=True).first()
                        if plan:
                            print(f"[REGISTRO-DEBUG] Plan por defecto encontrado: {plan.name}")
                    
                    if plan:
                        print(f"[REGISTRO-DEBUG] Entrando a crear suscripción...")
                        # Crear suscripción PENDIENTE (sin trial hasta que agregue tarjeta)
                        subscription = Subscription.objects.create(
                            user=user,
                            plan=plan,
                            status='pending',  # Estado pendiente, NO trial
                            trial_end=None,  # Sin fecha de trial todavía
                            current_period_start=None,
                            current_period_end=None
                        )
                        print(f"[REGISTRO-DEBUG] Suscripción PENDIENTE creada - ID: {subscription.id}")
                        print(f"[REGISTRO] Suscripción pendiente creada para {user.email} - Plan: {plan.name} - REQUIERE TARJETA")
                        
                        # Autenticar al usuario automáticamente
                        from django.contrib.auth import login as auth_login
                        auth_login(request, user)
                        print(f"[REGISTRO-DEBUG] Usuario autenticado")
                        
                        # Enviar email de bienvenida en background antes de redirigir
                        import threading
                        def enviar_email_async():
                            try:
                                nombre_completo = f"{nombre} {apellido}".strip()
                                enviar_informe_bienvenida(email, nombre_completo)
                                print(f"✅ Correo de bienvenida enviado a {email}")
                            except Exception as e:
                                print(f"Error enviando correo: {e}")
                        
                        thread = threading.Thread(target=enviar_email_async)
                        thread.daemon = True
                        thread.start()
                        print(f"[REGISTRO-DEBUG] Email thread iniciado")
                        
                        # Redirigir a Flow para agregar método de pago
                        messages.warning(request, f"¡Último paso! Agrega tu tarjeta para activar tu período de prueba gratuito de 7 días. No se te cobrará hasta que termine el trial.")
                        print(f"[REGISTRO-DEBUG] ============ REDIRIGIENDO A PAYMENT METHOD ============")
                        sys.stdout.flush()
                        return redirect('/subscription/add-payment-method/')  # URL absoluta
                    else:
                        print(f"[REGISTRO] ERROR: No se encontró ningún plan")
                        sys.stdout.flush()
                        raise Exception("No se pudo encontrar un plan de suscripción")
                
                except Exception as subscription_error:
                    print(f"[REGISTRO-ERROR] Error creando suscripción: {str(subscription_error)}")
                    import traceback
                    print(f"[REGISTRO-ERROR] Traceback: {traceback.format_exc()}")
                    sys.stdout.flush()
                    
                # Si falla la creación de la suscripción, mostrar página de éxito normal
                # Enviar email de bienvenida de todas formas
                import threading
                def enviar_email_async():
                    try:
                        nombre_completo = f"{nombre} {apellido}".strip()
                        enviar_informe_bienvenida(email, nombre_completo)
                        print(f"✅ Correo de bienvenida enviado a {email}")
                    except Exception as e:
                        print(f"Error enviando correo: {e}")
                
                thread = threading.Thread(target=enviar_email_async)
                thread.daemon = True
                thread.start()
                
                response = render(request, 'alerts/registro_exitoso_partial.html')
                return response
                
            except Exception as e:
                # Si algo falla, eliminar el usuario creado
                print(f"[REGISTRO-ERROR] Exception en bloque principal: {str(e)}")
                sys.stdout.flush()
                if 'user' in locals():
                    user.delete()
                messages.error(request, f'Error durante el registro: {str(e)}')
                return render(request, 'alerts/registro_prueba_chennai.html', {'form': form, 'plan': plan_slug})
        else:
            print(f"[REGISTRO-TEST] Form NO es válido. Errores: {form.errors}")
            sys.stdout.flush()
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        print(f"[REGISTRO-TEST] GET request - mostrando formulario")
        sys.stdout.flush()
        form = RegistroPruebaForm()
    
    print(f"[REGISTRO-TEST] Retornando template registro_prueba_chennai.html")
    sys.stdout.flush()
    return render(request, 'alerts/registro_prueba_chennai.html', {'form': form, 'plan': plan_slug})

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
    
    if request.method == 'POST':
        if 'eliminar_usuario' in request.POST:
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                # Obtener información antes de eliminar
                email = user.email
                
                # Eliminar organizaciones asociadas (esto elimina en cascada destinatarios)
                Organizacion.objects.filter(admin=user).delete()
                
                # Eliminar el usuario
                user.delete()
                
                messages.success(request, f'Usuario {email} y todos sus datos asociados han sido eliminados.')
            except User.DoesNotExist:
                messages.error(request, 'Usuario no encontrado.')
        
        elif 'eliminar_organizacion' in request.POST:
            org_id = request.POST.get('org_id')
            try:
                org = Organizacion.objects.get(id=org_id)
                nombre = org.nombre
                
                # Eliminar organización (elimina en cascada los destinatarios)
                org.delete()
                
                messages.success(request, f'Organización {nombre} y sus destinatarios han sido eliminados.')
            except Organizacion.DoesNotExist:
                messages.error(request, 'Organización no encontrada.')
        
        elif 'eliminar_destinatario' in request.POST:
            dest_id = request.POST.get('dest_id')
            try:
                dest = Destinatario.objects.get(id=dest_id)
                email = dest.email
                dest.delete()
                messages.success(request, f'Destinatario {email} ha sido eliminado.')
            except Destinatario.DoesNotExist:
                messages.error(request, 'Destinatario no encontrado.')
        
        return redirect('alerts:admin_panel')
    
    # Obtener datos para mostrar
    usuarios = User.objects.prefetch_related('organizaciones').all().order_by('email')
    organizaciones = Organizacion.objects.select_related('admin').annotate(
        num_destinatarios=models.Count('destinatarios')
    ).order_by('nombre')
    destinatarios = Destinatario.objects.select_related('organizacion').all().order_by('email')
    
    return render(request, 'alerts/admin_panel.html', {
        'usuarios': usuarios,
        'organizaciones': organizaciones,
        'destinatarios': destinatarios
    })

def logout_view(request):
    """Vista personalizada de logout que acepta GET requests"""
    print(f"[LOGOUT] Usuario {request.user} cerrando sesión")
    auth_logout(request)
    print("[LOGOUT] Sesión cerrada, mostrando página de confirmación")
    return render(request, 'alerts/logout_success.html')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_dias_prueba(request, destinatario_id):
    """
    Vista exclusiva para superadministradores para editar los días de prueba de un destinatario
    """
    destinatario = get_object_or_404(Destinatario, id=destinatario_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'extender':
            dias_extra = int(request.POST.get('dias_extra', 0))
            if dias_extra > 0:
                # Extender fecha de fin de trial
                if not destinatario.fecha_fin_trial:
                    destinatario.fecha_fin_trial = timezone.now() + timedelta(days=dias_extra)
                else:
                    destinatario.fecha_fin_trial += timedelta(days=dias_extra)
                destinatario.save()
                messages.success(request, f'Se han agregado {dias_extra} días al período de prueba de {destinatario.nombre}.')
        
        elif accion == 'establecer':
            nueva_fecha = request.POST.get('nueva_fecha')
            if nueva_fecha:
                # Convertir string a datetime
                fecha_dt = datetime.strptime(nueva_fecha, '%Y-%m-%d')
                fecha_aware = timezone.make_aware(fecha_dt.replace(hour=23, minute=59, second=59))
                destinatario.fecha_fin_trial = fecha_aware
                destinatario.save()
                messages.success(request, f'Fecha de fin de prueba actualizada para {destinatario.nombre}.')
        
        elif accion == 'marcar_pagado':
            destinatario.es_pagado = True
            destinatario.save()
            messages.success(request, f'{destinatario.nombre} ha sido marcado como cliente pagado.')
        
        elif accion == 'quitar_pagado':
            destinatario.es_pagado = False
            destinatario.save()
            messages.success(request, f'{destinatario.nombre} ya no está marcado como cliente pagado.')
        
        elif accion == 'reiniciar':
            destinatario.fecha_inicio_trial = timezone.now()
            destinatario.fecha_fin_trial = timezone.now() + timedelta(days=7)
            destinatario.es_pagado = False
            destinatario.save()
            messages.success(request, f'Período de prueba reiniciado para {destinatario.nombre} (7 días desde hoy).')
        
        return redirect('alerts:admin_panel')
    
    # Calcular fecha sugerida para el input de fecha
    fecha_sugerida = (destinatario.fecha_fin_trial.date() if destinatario.fecha_fin_trial else 
                      (timezone.now() + timedelta(days=7)).date())
    
    return render(request, 'alerts/editar_dias_prueba.html', {
        'destinatario': destinatario,
        'fecha_sugerida': fecha_sugerida,
        'dias_restantes': destinatario.dias_restantes_trial(),
        'trial_activo': destinatario.trial_activo()
    }) 