# 🚨 PROBLEMAS ANTICIPADOS Y SOLUCIONES

## Estado Actual ✅
- **Timezone configurado**: America/Santiago en Heroku
- **Todos los scrapers**: Filtrado para día inmediatamente anterior
- **SEA**: Sin restricción de año (funciona para 2025)
- **Desplegado**: Versión v340 en Heroku

## 🔴 PROBLEMAS CRÍTICOS POTENCIALES

### 1. Timeout de Heroku (30 segundos)
**Problema**: Los dynos gratuitos de Heroku tienen límite de 30 segundos para requests HTTP
**Síntoma**: El informe no se genera o se corta a mitad del proceso
**Solución**:
```bash
# Opción 1: Usar un worker dyno (Procfile)
worker: python scripts/generators/generar_informe_oficial_integrado_mejorado.py

# Opción 2: Dividir el proceso en tareas más pequeñas
# Opción 3: Actualizar a dyno pago
```

### 2. Selenium Timeout en Heroku
**Problema**: Chrome/ChromeDriver puede ser lento en Heroku
**Síntoma**: Scrapers SEA/Contraloría fallan con timeout
**Solución**:
```python
# Aumentar timeouts en scrapers
wait = WebDriverWait(driver, 30)  # En vez de 10-15
```

## 🟠 PROBLEMAS DE ALTA PRIORIDAD

### 3. Sitios Web Caídos
**Problema**: Los sitios gubernamentales pueden estar no disponibles
**Sitios críticos**:
- Contraloría: https://www.contraloria.cl
- Congreso: https://www.camara.cl
- SEA: https://seia.sea.gob.cl
- CMF: https://www.cmfchile.cl
- SII: https://www.sii.cl

**Solución**:
```python
# Implementar reintentos
for intento in range(3):
    try:
        response = requests.get(url, timeout=20)
        break
    except:
        time.sleep(5)
```

### 4. Cambios en Estructura HTML
**Problema**: Los sitios web cambian su diseño/estructura
**Síntoma**: Scrapers no encuentran elementos esperados
**Monitoreo**: Ejecutar `python3 monitoreo_preventivo.py` regularmente

## 🟡 PROBLEMAS FRECUENTES

### 5. Fines de Semana y Feriados
**Problema**: No hay publicaciones oficiales
**Fechas especiales 2025**:
- Fines de semana: Sábados y Domingos
- Feriados:
  - 18-19 Septiembre (Fiestas Patrias)
  - 12 Octubre (Encuentro de Dos Mundos)
  - 31 Octubre (Día de las Iglesias Evangélicas)
  - 1 Noviembre (Todos los Santos)
  - 8 Diciembre (Inmaculada Concepción)
  - 25 Diciembre (Navidad)

**Solución**: Normal, el informe mostrará secciones vacías con mensaje explicativo

### 6. Datos Duplicados
**Problema**: Un proyecto aparece múltiples veces
**Causa**: Múltiples ejecuciones o scraping duplicado
**Solución**: Deduplicar por número/ID único

## 🔵 PROBLEMAS MENORES

### 7. Archivo CMF Vacío
**Archivo**: `data/hechos_cmf_selenium_reales.json`
**Solución**:
```bash
# Ejecutar scraper CMF manualmente
python3 scripts/scrapers/scraper_cmf_mejorado.py
```

### 8. Warnings de SSL
**Problema**: InsecureRequestWarning al conectar con sitios gubernamentales
**Solución**: Normal, los certificados gubernamentales a veces tienen problemas

## 📋 COMANDOS ÚTILES DE EMERGENCIA

### Verificar Estado
```bash
# Monitoreo preventivo
python3 monitoreo_preventivo.py

# Ver logs de Heroku
heroku logs --tail --app informediariochile

# Verificar configuración
heroku config --app informediariochile
```

### Ejecutar Manualmente
```bash
# Generar informe manual (local)
python3 scripts/generators/generar_informe_oficial_integrado_mejorado.py

# Ejecutar scraper específico
python3 scripts/scrapers/scraper_contraloria_reglamentos.py
python3 scripts/scrapers/scraper_proyectos_ley_integrado.py
```

### Reiniciar Heroku
```bash
# Reiniciar dyno
heroku restart --app informediariochile

# Escalar dynos
heroku ps:scale web=0 --app informediariochile
heroku ps:scale web=1 --app informediariochile
```

## 🚀 ACCIONES PREVENTIVAS RECOMENDADAS

1. **Diariamente**: Revisar que el informe se generó correctamente
2. **Semanalmente**: Ejecutar `monitoreo_preventivo.py`
3. **Mensualmente**: Verificar actualizaciones en sitios web
4. **Ante fallas**: 
   - Revisar logs: `heroku logs --tail`
   - Ejecutar monitoreo: `python3 monitoreo_preventivo.py`
   - Verificar sitios web manualmente

## 📞 CONTACTO PARA EMERGENCIAS

Si el sistema falla completamente:
1. Revisar este documento
2. Ejecutar monitoreo preventivo
3. Revisar logs de Heroku
4. Ejecutar manualmente si es necesario

## ✅ CONFIRMACIÓN FINAL

El sistema está configurado correctamente para:
- Buscar SOLO datos del día inmediatamente anterior
- Funcionar con fechas del 2025
- Manejar errores comunes
- Generar informes automáticamente a las 9:00 AM Chile

**Última verificación**: 29/08/2025
**Estado**: ✅ Operacional