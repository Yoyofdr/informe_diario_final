# Guía de Instalación

## Requisitos Previos

- Python 3.11 o superior
- PostgreSQL
- Git
- Cuenta de OpenAI (para API key)

## Instalación Local

### 1. Clonar el repositorio

```bash
git clone https://github.com/Yoyofdr/informe-diario-chile.git
cd informe-diario-chile
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp config/.env.example .env
```

Editar `.env` con tus credenciales:

- `OPENAI_API_KEY`: Tu API key de OpenAI
- `HOSTINGER_EMAIL_PASSWORD`: Contraseña del email
- `DATABASE_URL`: URL de PostgreSQL (opcional para desarrollo)

### 5. Configurar base de datos

```bash
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

### 7. Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en http://localhost:8000

## Instalación en Producción (Heroku)

### 1. Crear aplicación en Heroku

```bash
heroku create tu-app-nombre
```

### 2. Agregar PostgreSQL

```bash
heroku addons:create heroku-postgresql:hobby-dev
```

### 3. Configurar variables de entorno

```bash
heroku config:set OPENAI_API_KEY="tu-api-key"
heroku config:set HOSTINGER_EMAIL_PASSWORD="tu-password"
heroku config:set EMAIL_FROM="contacto@informediariochile.cl"
```

### 4. Deploy

```bash
git push heroku main
```

### 5. Ejecutar migraciones

```bash
heroku run python manage.py migrate
```

### 6. Crear superusuario

```bash
heroku run python manage.py createsuperuser
```

## Verificación

Para verificar que todo funciona:

```bash
# Desarrollo
python manage.py check

# Producción
heroku run python manage.py check --deploy
```