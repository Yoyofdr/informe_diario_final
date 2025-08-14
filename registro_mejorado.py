"""
Versión mejorada del proceso de registro con:
1. Todo dentro de una sola transacción atómica
2. Reintentos automáticos
3. Logging detallado
4. Verificación antes de mostrar éxito
5. Manejo robusto de errores
"""

def registro_prueba_mejorado(request):
    if request.method == 'POST':
        form = RegistroPruebaForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            apellido = form.cleaned_data['apellido']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data['telefono']
            empresa_nombre = form.cleaned_data['empresa']
            password = form.cleaned_data['password1']
            
            # Extraer dominio del email
            dominio = email.split('@')[1].lower().strip()
            
            # Verificar email duplicado
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un usuario con ese email.')
                return render(request, 'alerts/registro_prueba_chennai.html', {'form': form})
            
            # Intentar registro con reintentos
            import time
            import logging
            
            logger = logging.getLogger('registro')
            max_intentos = 3
            intento_actual = 0
            registro_exitoso = False
            ultimo_error = None
            
            while intento_actual < max_intentos and not registro_exitoso:
                intento_actual += 1
                logger.info(f"[REGISTRO] Intento {intento_actual} de {max_intentos} para {email}")
                
                try:
                    with transaction.atomic():
                        # 1. Crear usuario
                        logger.info(f"[REGISTRO] Creando usuario: {email}")
                        user = User.objects.create_user(
                            username=email,
                            email=email,
                            password=password,
                            first_name=nombre,
                            last_name=apellido
                        )
                        logger.info(f"[REGISTRO] Usuario creado con ID: {user.id}")
                        
                        # 2. Crear o buscar organización
                        org = Organizacion.objects.filter(dominio=dominio).first()
                        
                        if not org:
                            # Crear nueva organización
                            logger.info(f"[REGISTRO] Creando nueva organización para dominio: {dominio}")
                            org = Organizacion.objects.create(
                                nombre=empresa_nombre,
                                dominio=dominio,
                                admin=user,
                                suscripcion_activa=True
                            )
                            logger.info(f"[REGISTRO] Organización creada: {org.nombre} (ID: {org.id})")
                        else:
                            # Usar organización existente
                            logger.info(f"[REGISTRO] Usando org existente para {dominio}: {org.nombre}")
                            # Si no tiene admin, asignar este usuario
                            if not org.admin:
                                org.admin = user
                                org.save()
                                logger.info(f"[REGISTRO] Usuario asignado como admin de org existente")
                        
                        # 3. Crear destinatario
                        logger.info(f"[REGISTRO] Creando destinatario para org: {org.id}")
                        destinatario = Destinatario.objects.create(
                            nombre=f"{nombre} {apellido}".strip() or user.username,
                            email=email,
                            organizacion=org
                        )
                        logger.info(f"[REGISTRO] Destinatario creado con ID: {destinatario.id}")
                        
                        # 4. Verificación dentro de la transacción
                        # Esto garantiza que los datos están en la DB antes de commit
                        user_check = User.objects.filter(id=user.id).exists()
                        org_check = Organizacion.objects.filter(id=org.id).exists()
                        dest_check = Destinatario.objects.filter(id=destinatario.id).exists()
                        
                        if not (user_check and org_check and dest_check):
                            raise Exception(
                                f"Verificación fallida - User: {user_check}, "
                                f"Org: {org_check}, Dest: {dest_check}"
                            )
                        
                        logger.info(f"[REGISTRO] Verificación dentro de transacción OK")
                        
                        # Si llegamos aquí, todo está bien
                        registro_exitoso = True
                        
                    # Fin de transaction.atomic() - aquí se hace el COMMIT
                    
                except Exception as e:
                    ultimo_error = str(e)
                    logger.error(f"[REGISTRO] Error en intento {intento_actual}: {e}")
                    
                    if intento_actual < max_intentos:
                        # Esperar antes de reintentar
                        tiempo_espera = intento_actual * 2  # 2, 4 segundos
                        logger.info(f"[REGISTRO] Esperando {tiempo_espera} segundos antes de reintentar...")
                        time.sleep(tiempo_espera)
                    
                    # Limpiar cualquier usuario parcialmente creado
                    try:
                        User.objects.filter(email=email).delete()
                    except:
                        pass
            
            # Después de todos los intentos
            if registro_exitoso:
                # VERIFICACIÓN FINAL fuera de la transacción
                try:
                    user_final = User.objects.get(email=email)
                    org_final = Organizacion.objects.filter(
                        models.Q(admin=user_final) | models.Q(dominio=dominio)
                    ).first()
                    dest_final = Destinatario.objects.filter(email=email).first()
                    
                    if not (user_final and org_final and dest_final):
                        raise Exception(
                            f"Verificación final fallida - "
                            f"User: {bool(user_final)}, "
                            f"Org: {bool(org_final)}, "
                            f"Dest: {bool(dest_final)}"
                        )
                    
                    logger.info(
                        f"[REGISTRO] ✅ ÉXITO COMPLETO - "
                        f"Usuario ID: {user_final.id}, "
                        f"Org ID: {org_final.id}, "
                        f"Dest ID: {dest_final.id}"
                    )
                    
                    # Enviar emails en background
                    import threading
                    
                    def enviar_emails_background():
                        try:
                            nombre_completo = f"{nombre} {apellido}".strip()
                            enviar_informe_bienvenida(email, nombre_completo)
                            logger.info(f"[REGISTRO] Email de bienvenida enviado a {email}")
                        except Exception as e:
                            logger.error(f"[REGISTRO] Error enviando email de bienvenida: {e}")
                    
                    thread = threading.Thread(target=enviar_emails_background)
                    thread.daemon = True
                    thread.start()
                    
                    # Mostrar página de éxito
                    return render(request, 'alerts/registro_exitoso_partial.html')
                    
                except Exception as e:
                    logger.error(f"[REGISTRO] ERROR CRÍTICO en verificación final: {e}")
                    messages.error(
                        request, 
                        "Tu registro se completó pero hubo un problema de verificación. "
                        "Por favor, intenta iniciar sesión o contacta soporte."
                    )
                    return render(request, 'alerts/registro_prueba_chennai.html', {'form': form})
            else:
                # Todos los intentos fallaron
                logger.error(f"[REGISTRO] FALLO TOTAL después de {max_intentos} intentos. Último error: {ultimo_error}")
                messages.error(
                    request,
                    "No pudimos completar tu registro en este momento. "
                    "Por favor, intenta nuevamente en unos minutos. "
                    f"Si el problema persiste, contacta soporte con este código: REG-{intento_actual}-{email[:5]}"
                )
                return render(request, 'alerts/registro_prueba_chennai.html', {'form': form})
        else:
            # Formulario no válido
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = RegistroPruebaForm()
    
    return render(request, 'alerts/registro_prueba_chennai.html', {'form': form})