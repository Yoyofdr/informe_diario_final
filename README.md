# Informe Diario Chile

Sistema automatizado de análisis y resumen del Diario Oficial, CMF y SII de Chile.

## 🚀 Características

- **Análisis automatizado** del Diario Oficial de Chile
- **Monitoreo de hechos esenciales** de la CMF (Comisión para el Mercado Financiero)
- **Seguimiento de normativas** del SII (Servicio de Impuestos Internos)
- **Resúmenes inteligentes** generados con IA
- **Envío automático** de informes por email
- **Panel de administración** para gestionar suscriptores

## 📋 Requisitos

- Python 3.11+
- PostgreSQL
- Cuenta de OpenAI API
- Servidor SMTP para envío de emails

## 🛠️ Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/Yoyofdr/informe-diario-chile.git
cd informe-diario-chile
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

5. Ejecutar migraciones:
```bash
python manage.py migrate
```

6. Crear superusuario:
```bash
python manage.py createsuperuser
```

7. Ejecutar servidor:
```bash
python manage.py runserver
```

## 🔧 Configuración

### Variables de entorno requeridas:

```env
# Base de datos
DATABASE_URL=postgres://usuario:password@host:puerto/nombre_db

# Email
HOSTINGER_EMAIL_PASSWORD=tu_password
EMAIL_FROM=contacto@informediariochile.cl
SMTP_SERVER=smtp.hostinger.com
SMTP_PORT=587

# APIs
OPENAI_API_KEY=tu_api_key

# Django
SECRET_KEY=tu_secret_key
DEBUG=False
ALLOWED_HOSTS=informediariochile.com,www.informediariochile.cl
```

## 📦 Estructura del proyecto

```
informe-diario-chile/
├── alerts/                 # App principal de Django
│   ├── models.py          # Modelos de datos
│   ├── views.py           # Vistas y lógica
│   ├── scraper_diario_oficial.py  # Scraper del Diario Oficial
│   └── cmf_resumenes_ai.py        # Procesamiento de CMF
├── templates/             # Plantillas HTML
│   ├── alerts/           # Plantillas de la app
│   └── registration/     # Plantillas de autenticación
├── static/               # Archivos estáticos
├── generar_informe_oficial_integrado_mejorado.py  # Script principal
├── scraper_cmf_mejorado.py  # Scraper de CMF
└── manage.py            # Django management
```

## 🚀 Uso

### Generar informe manual:

```bash
python generar_informe_oficial_integrado_mejorado.py
```

### Programar envío automático (Heroku Scheduler):

```bash
python manage.py enviar_informes_diarios
```

## 📧 Formato de informes

Los informes incluyen:

1. **Diario Oficial**:
   - Normas Generales
   - Normas Particulares  
   - Avisos Destacados

2. **CMF**:
   - Hechos esenciales de empresas IPSA
   - Comunicados relevantes

3. **SII**:
   - Nuevas circulares
   - Resoluciones importantes

## 🔐 Seguridad

- Nunca commits credenciales o API keys
- Usa variables de entorno para información sensible
- Mantén actualizado el archivo `.gitignore`

## 🤝 Contribuir

1. Fork el proyecto
2. Crea tu rama (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -m 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

## 📄 Licencia

Proyecto privado - Todos los derechos reservados

## 📞 Contacto

Para consultas: contacto@informediariochile.cl