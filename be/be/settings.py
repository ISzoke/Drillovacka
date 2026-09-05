"""
================================================================================
 Module: settings.py
 Description:
        Core configuration of the project. 
        - environment variables loading
        - database settings
        - installed apps
        - middleware
        - ASGI setup
        - static files handling

 Author: Dominik Horut (xhorut01)
================================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))
AZURE_API_KEY = os.getenv('AZURE_API_KEY')
AZURE_REGION = os.getenv('AZURE_REGION')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-3zibbwj&l%j)_dh%+*tr*xvx^uun)z3=bcq35ps#d7p%ktvzgz')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False 

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'api',
    'rest_framework',
    'corsheaders',
    'channels',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'be.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'static')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', '6379')))],
        },
    },
}

WSGI_APPLICATION = 'be.wsgi.application'
ASGI_APPLICATION = 'be.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQLDATABASE'),
        'USER': os.getenv('MYSQLUSER'),
        'PASSWORD': os.getenv('MYSQLPASSWORD'),
        'HOST': os.getenv('MYSQLHOST', 'db'),
        'PORT': os.getenv('MYSQLPORT', '3307'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Host / CORS settings — both used to be wide open (ALLOWED_HOSTS=['*'],
# CORS_ALLOW_ALL_ORIGINS=True) even though docker-compose.yml already passes
# a real ALLOWED_HOSTS env var that was simply never read here. With CORS wide
# open, any third-party website's JS could call every API endpoint using a
# visitor's own browser as an unwitting, distributed source — that's what
# turned "no rate limiting" into "trivially abusable from anywhere" for the
# paid Gemini/Azure endpoints. Derive both from the same host list so no new
# env var/deploy step is needed.
_allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '').strip()
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()] or ['localhost', '127.0.0.1']

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = []
for _host in ALLOWED_HOSTS:
    if _host in ('localhost', '127.0.0.1'):
        CORS_ALLOWED_ORIGINS += [f'http://{_host}:5173', f'http://{_host}:8000', f'http://{_host}']
    else:
        CORS_ALLOWED_ORIGINS += [f'https://{_host}', f'http://{_host}']

# Email (SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'false').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@aritmation.com')
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


