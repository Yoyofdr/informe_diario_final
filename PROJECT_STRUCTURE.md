# Estructura del Proyecto

```
informe-diario-chile/
├── alerts/                      # App principal de Django
│   ├── management/             # Comandos de Django
│   │   └── commands/          # Comandos personalizados
│   ├── migrations/            # Migraciones de BD
│   ├── services/              # Servicios auxiliares
│   ├── utils/                 # Utilidades
│   ├── models.py              # Modelos de datos
│   ├── views.py               # Vistas
│   ├── urls.py                # URLs de la app
│   ├── forms.py               # Formularios
│   ├── admin.py               # Admin de Django
│   ├── scraper_diario_oficial.py  # Scraper DO
│   ├── scraper_sii.py         # Scraper SII
│   ├── cmf_criterios_profesionales.py
│   ├── cmf_resumenes_ai.py
│   └── evaluador_relevancia.py
│
├── config/                     # Configuraciones
│   └── .env.example           # Plantilla de variables
│
├── data/                       # Archivos de datos
│   ├── edition_cache.json     # Cache de ediciones
│   └── hechos_cmf_selenium_reales.json
│
├── docs/                       # Documentación
│   ├── CLAUDE.md              # Instrucciones IA
│   ├── INSTALLATION.md        # Guía instalación
│   └── USAGE.md               # Guía de uso
│
├── market_sniper/              # Configuración Django
│   ├── settings.py            # Settings principal
│   ├── urls.py                # URLs principales
│   └── wsgi.py                # WSGI
│
├── scripts/                    # Scripts ejecutables
│   ├── generators/            # Generadores de informes
│   │   └── generar_informe_oficial_integrado_mejorado.py
│   └── scrapers/              # Scrapers externos
│       └── scraper_cmf_mejorado.py
│
├── static/                     # Archivos estáticos
│   └── img/                   # Imágenes
│
├── templates/                  # Plantillas HTML
│   ├── alerts/                # Plantillas de la app
│   │   ├── dashboard.html
│   │   ├── landing_explicativa.html
│   │   ├── registro_prueba.html
│   │   └── email/
│   ├── registration/          # Plantillas de auth
│   │   └── login.html
│   └── informe_diario_oficial_plantilla.html
│
├── .gitignore                 # Archivos ignorados
├── manage.py                  # Django management
├── Procfile                   # Config Heroku
├── README.md                  # Documentación principal
├── requirements.txt           # Dependencias Python
└── runtime.txt               # Versión Python
```

## Carpetas principales

### `/alerts`
Aplicación Django principal que contiene toda la lógica del negocio.

### `/scripts`
Scripts independientes organizados por función:
- `generators/`: Scripts que generan informes
- `scrapers/`: Scripts que obtienen datos externos

### `/data`
Archivos JSON y datos persistentes:
- Cache de ediciones del Diario Oficial
- Hechos esenciales de CMF

### `/templates`
Plantillas HTML organizadas por aplicación:
- `alerts/`: Plantillas específicas de la app
- `registration/`: Plantillas de autenticación
- Plantilla principal del informe en la raíz

### `/docs`
Documentación completa del proyecto:
- Guías de instalación y uso
- Instrucciones para la IA
- Documentación técnica

## Flujo de datos

1. **Scrapers** obtienen datos de fuentes externas
2. **Generadores** procesan y formatean los datos
3. **Django** gestiona usuarios y envíos
4. **Templates** dan formato a los emails
5. **Data** almacena cache y datos temporales