import sys
from pathlib import Path

import dj_database_url

from core.env import env_settings

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / 'apps'))

SECRET_KEY = env_settings.SECRET_KEY
DEBUG = env_settings.DEBUG

ALLOWED_HOSTS = env_settings.ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = env_settings.CSRF_TRUSTED_ORIGINS

# Security Settings
SESSION_COOKIE_SECURE = env_settings.SESSION_COOKIE_SECURE
CSRF_COOKIE_SECURE = env_settings.CSRF_COOKIE_SECURE


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'django_cotton',
    'widget_tweaks',
    # Local apps
    'accounts',
    'schedule',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.PerformanceLogMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'static'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'core.asgi.application'


# Database

DATABASES = {
    'default': dj_database_url.parse(
        env_settings.DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    ),
}


# Password validation

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
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

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'signin'

# Internationalization

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
WHITENOISE_MANIFEST_STRICT = False


# Media files (uploads)

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

COTTON_DIR = 'components'

# Logging Configuration for Production (Railway, Heroku, etc.)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env_settings.LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env_settings.LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Captura erros e logs dos seus apps locais (accounts, schedule, etc)
        'accounts': {
            'handlers': ['console'],
            'level': env_settings.LOG_LEVEL,
            'propagate': False,
        },
        'schedule': {
            'handlers': ['console'],
            'level': env_settings.LOG_LEVEL,
            'propagate': False,
        },
    },
}

# Django Debug Toolbar
if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(
        MIDDLEWARE.index('django.middleware.common.CommonMiddleware') + 1,
        'debug_toolbar.middleware.DebugToolbarMiddleware'
    )
    
    # Em produção (Railway), o IP do cliente muda por causa do proxy reverso.
    # Para forçar a exibição da barra quando DEBUG=True, usamos uma função customizada.
    def show_toolbar(request):
        return True
        
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': 'core.settings.show_toolbar',
    }
