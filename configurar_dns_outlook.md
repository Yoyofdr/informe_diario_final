# 🔧 CONFIGURACIÓN DNS PARA MEJORAR ENTREGABILIDAD EN OUTLOOK

## ⚠️ CAMBIOS URGENTES EN DNS (Hostinger)

### 1. **ACTIVAR DKIM** (MÁS IMPORTANTE)
1. Entra a tu panel de Hostinger
2. Ve a la sección de Email → DKIM
3. Activa DKIM para `informediariochile.cl`
4. Hostinger te dará 2 registros CNAME, algo como:
   ```
   s1._domainkey.informediariochile.cl → s1.domainkey.uXXXXX.hostinger.com
   s2._domainkey.informediariochile.cl → s2.domainkey.uXXXXX.hostinger.com
   ```
5. Agrega estos CNAME en tu zona DNS

### 2. **ACTUALIZAR SPF** (cambiar ~all a -all)
Busca el registro TXT actual:
```
v=spf1 include:_spf.mail.hostinger.com ~all
```

Cámbialo a:
```
v=spf1 include:_spf.mail.hostinger.com -all
```

### 3. **ACTUALIZAR DMARC** (de p=none a p=quarantine)
Busca el registro TXT en `_dmarc.informediariochile.cl`:
```
v=DMARC1; p=none
```

Cámbialo a:
```
v=DMARC1; p=quarantine; pct=100; adkim=s; aspf=s; rua=mailto:dmarc@informediariochile.cl; fo=1
```

### 4. **CREAR BUZONES DE REPORTE** (opcional pero recomendado)
Crea estas direcciones de email (pueden redirigir a tu email principal):
- `dmarc@informediariochile.cl` - Para reportes DMARC
- `abuse@informediariochile.cl` - Requerido por RFC
- `postmaster@informediariochile.cl` - Requerido por RFC

## 📊 VERIFICACIÓN

### Después de hacer los cambios DNS, verifica con:

1. **SPF**: https://mxtoolbox.com/spf.aspx
   - Busca: `informediariochile.cl`
   - Debe mostrar: ✅ SPF Record Published

2. **DKIM**: https://mxtoolbox.com/dkim.aspx
   - Dominio: `informediariochile.cl`
   - Selector: `s1` (o el que te dé Hostinger)
   - Debe mostrar: ✅ DKIM Record Published

3. **DMARC**: https://mxtoolbox.com/dmarc.aspx
   - Busca: `informediariochile.cl`
   - Debe mostrar: ✅ DMARC Record Published

## 🚀 TIMELINE ESPERADO

- **Inmediato**: SPF y DMARC funcionan al cambiar DNS
- **1-4 horas**: DKIM empieza a funcionar tras propagación
- **24-48 horas**: Microsoft empieza a ver mejor reputación
- **7-14 días**: Con throttling, la entregabilidad mejora significativamente

## 📝 NOTAS IMPORTANTES

1. **NO cambies a p=reject todavía** - Espera 2 semanas con p=quarantine
2. **El código ya está actualizado** con:
   - Headers correctos (Message-ID, Date)
   - Throttling automático para Microsoft (20/min)
   - List-Unsubscribe headers
3. **Pide a 1-2 clientes con Outlook** que:
   - Agreguen `contacto@informediariochile.cl` a remitentes seguros
   - Revisen spam/cuarentena los primeros días

## ✅ CHECKLIST RÁPIDO

- [ ] Activar DKIM en Hostinger
- [ ] Agregar los 2 CNAME de DKIM al DNS
- [ ] Cambiar SPF de `~all` a `-all`
- [ ] Actualizar DMARC con la configuración completa
- [ ] Esperar propagación DNS (1-4 horas)
- [ ] Verificar con MXToolbox
- [ ] Desplegar el código actualizado con throttling