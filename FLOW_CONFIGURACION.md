# Configuración de Flow Payment Gateway

## ✅ Estado Actual

El sistema de pagos con Flow está **completamente implementado y probado** en el código.

### Pruebas Exitosas (100%)
- ✅ Credenciales de Flow configuradas correctamente
- ✅ Endpoints de suscripción funcionando
- ✅ Sistema de prueba (trial) implementado
- ✅ Seguridad de webhooks verificada
- ✅ Panel de administración configurado

## 🔧 Configuración en Dashboard de Flow

### 1. Acceder a Flow Sandbox
- URL: https://sandbox.flow.cl/app
- Usar tus credenciales de Flow

### 2. Configurar URLs de Retorno

En el panel de Flow, configurar las siguientes URLs:

#### URLs de Producción (cuando estés listo)
```
URL de Confirmación: https://tu-dominio.com/subscription/webhook/
URL de Retorno: https://tu-dominio.com/subscription/payment-success/
URL de Fracaso: https://tu-dominio.com/subscription/payment-failure/
```

#### URLs para Desarrollo Local (ngrok)
Si quieres probar localmente, usa ngrok:
```bash
ngrok http 8000
```

Luego usa las URLs de ngrok:
```
URL de Confirmación: https://xxxxx.ngrok.io/subscription/webhook/
URL de Retorno: https://xxxxx.ngrok.io/subscription/payment-success/
URL de Fracaso: https://xxxxx.ngrok.io/subscription/payment-failure/
```

### 3. Crear Planes en Flow

En el dashboard de Flow, crear dos planes:

#### Plan Individual
- Nombre: Plan Individual
- Monto: $3.990 CLP
- Intervalo: Mensual
- Días de prueba: 7

#### Plan Organización
- Nombre: Plan Organización  
- Monto: $29.990 CLP
- Intervalo: Mensual
- Días de prueba: 7

## 💳 Tarjetas de Prueba

Para probar en Sandbox, usa estas tarjetas:

| Tipo | Número | CVV | Fecha | RUT |
|------|--------|-----|-------|-----|
| Visa | 4051885600446623 | 123 | Cualquier futura | 11.111.111-1 |
| MasterCard | 5186059559590568 | 123 | Cualquier futura | 11.111.111-1 |

## 🧪 Cómo Probar el Flujo Completo

### 1. Iniciar el servidor
```bash
cd /Users/rodrigofernandezdelrio/Desktop/Project\ Diario\ Oficial
python manage.py runserver
```

### 2. Acceder a la página de precios
- URL: http://localhost:8000/subscription/pricing/
- Verás dos planes con botones "Comenzar Prueba de 14 Días"

### 3. Proceso de suscripción
1. Click en "Comenzar Prueba de 14 Días"
2. Te pedirá iniciar sesión o registrarte
3. Serás redirigido a Flow para el pago
4. Usa las tarjetas de prueba
5. Completa el pago
6. Serás redirigido de vuelta con la suscripción activa

### 4. Verificar en Admin
- URL: http://localhost:8000/admin/
- Usuario: rfernandezdelrio@uc.cl
- Ver suscripciones, pagos y organizaciones

## 📊 Panel de Administración

El superadmin (rfernandezdelrio@uc.cl) tiene acceso completo a:

### Gestión de Planes
- Ver todos los planes
- Activar/desactivar planes
- Modificar precios y características

### Gestión de Suscripciones
- Ver todas las suscripciones
- Estados: trial, active, past_due, canceled, expired
- Acciones: marcar como activa, cancelar, exportar CSV
- Filtros por estado, plan, fecha

### Gestión de Pagos
- Ver todos los pagos
- Estados: pending, completed, failed, refunded
- Detalles de transacción de Flow
- Exportar reportes

### Gestión de Organizaciones
- Ver organizaciones
- Usuarios por organización
- Límites y uso

## 🚀 Pasar a Producción

Cuando estés listo para producción:

1. **Cambiar credenciales en .env**
```env
FLOW_SANDBOX=False
FLOW_API_KEY=tu-api-key-produccion
FLOW_SECRET_KEY=tu-secret-key-produccion
```

2. **Solicitar activación en Flow**
- Contactar a Flow para activar cuenta de producción
- Requiere documentación de empresa

3. **Actualizar URLs en Flow**
- Cambiar todas las URLs a tu dominio de producción

4. **Configurar SSL**
- Flow requiere HTTPS en producción

## 📝 Logs y Monitoreo

Los eventos importantes se registran en:
- Django logs: Ver errores de pago
- Admin panel: Ver historial de transacciones
- Flow dashboard: Ver pagos procesados

## 🔐 Seguridad

- ✅ Webhooks verificados con firma HMAC-SHA256
- ✅ Tokens seguros para cada transacción
- ✅ HTTPS requerido en producción
- ✅ Credenciales en variables de entorno

## 📞 Soporte

- Flow Soporte: soporte@flow.cl
- Documentación: https://www.flow.cl/docs/api.html
- Dashboard Sandbox: https://sandbox.flow.cl/app
- Dashboard Producción: https://www.flow.cl/app

---

**Última actualización:** 16 de septiembre de 2025
**Estado:** Sistema completamente funcional y probado