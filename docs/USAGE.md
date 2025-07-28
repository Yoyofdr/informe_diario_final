# Guía de Uso

## Generación de Informes

### Informe Manual

Para generar un informe manualmente:

```bash
# Informe de hoy
python scripts/generators/generar_informe_oficial_integrado_mejorado.py

# Informe de fecha específica
python scripts/generators/generar_informe_oficial_integrado_mejorado.py "21-07-2025"
```

### Informe Automático

El sistema envía informes automáticamente todos los días a las 9:00 AM (hora de Chile).

Para ejecutar el envío manual:

```bash
python manage.py enviar_informes_diarios
```

## Panel de Administración

### Acceso

1. Ir a `/admin/`
2. Ingresar con credenciales de superusuario

### Gestión de Usuarios

- Crear nuevos usuarios
- Asignar organizaciones
- Gestionar permisos

### Gestión de Organizaciones

- Crear organizaciones
- Agregar destinatarios
- Configurar planes de suscripción

## API de Scraping

### Diario Oficial

```python
from alerts.scraper_diario_oficial import obtener_sumario_diario_oficial

# Obtener sumario de hoy
resultado = obtener_sumario_diario_oficial()

# Obtener sumario de fecha específica
resultado = obtener_sumario_diario_oficial("21-07-2025")
```

### CMF

```python
from scripts.scrapers.scraper_cmf_mejorado import scrape_hechos_esenciales

# Obtener hechos esenciales
hechos = scrape_hechos_esenciales()
```

### SII

```python
from alerts.scraper_sii import obtener_documentos_sii

# Obtener documentos del SII
documentos = obtener_documentos_sii()
```

## Comandos Django

### Envío de informes

```bash
# Enviar informes diarios
python manage.py enviar_informes_diarios

# Scraping de hechos esenciales
python manage.py scrape_hechos

# Importar empresas
python manage.py importar_empresas archivo.csv

# Clasificar empresas
python manage.py clasificar_empresas
```

## Configuración de Email

Los emails se envían desde `contacto@informediariochile.cl` usando SMTP de Hostinger.

Para cambiar la configuración, editar `.env`:

```env
EMAIL_FROM=nuevo-email@dominio.cl
SMTP_SERVER=smtp.servidor.com
SMTP_PORT=587
```

## Solución de Problemas

### Error de API Key

Si ves errores relacionados con OpenAI:

1. Verificar que `.env` tenga `OPENAI_API_KEY`
2. Verificar que la API key sea válida
3. Revisar límites de uso en OpenAI

### Error de Email

Si los emails no se envían:

1. Verificar credenciales en `.env`
2. Verificar que el servidor SMTP esté activo
3. Revisar logs con `heroku logs --tail`

### Error de Base de Datos

Si hay problemas con la base de datos:

1. Verificar `DATABASE_URL` en `.env`
2. Ejecutar migraciones: `python manage.py migrate`
3. Verificar conexión: `python manage.py dbshell`