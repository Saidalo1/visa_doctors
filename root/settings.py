from os.path import join
from pathlib import Path

import sentry_sdk
from django.utils.translation import gettext_lazy as _
from environ import Env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Django Environment
env = Env()
env.read_env('.env')

# Sentry Configuration
sentry_sdk.init(
    dsn=env.str('SENTRY_DSN', default=''),
    send_default_pii=True,
    traces_sample_rate=1.0,
    _experiments={
        "continuous_profiling_auto_start": True,
    },
    environment='development' if env.bool('DEBUG', False) else 'production',
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost'])

# Application definition
INSTALLED_APPS = [
    # Multilanguage
    'modeltranslation',

    # Django Jazzmin for admin panel
    'jazzmin',

    # Default applications
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # My apps
    'app.apps.AppConfig',

    # Third-party apps
    'corsheaders',
    'debug_toolbar',
    'django_ckeditor_5',
    'rest_framework',
    'drf_spectacular',
    'import_export',
    'safedelete',

]

MIDDLEWARE = [
    # Default middlewares
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # MultiLanguageMiddleware
    'django.middleware.locale.LocaleMiddleware',

    # Django Debug Toolbar
    'debug_toolbar.middleware.DebugToolbarMiddleware',

    # CORS Middleware
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'root.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': env.bool('TEMPLATE_APP_DIR', True),
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

WSGI_APPLICATION = 'root.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': env.str('SQL_ENGINE'),
        'NAME': env.str('SQL_NAME'),
        'USER': env.str('SQL_USER'),
        'PASSWORD': env.str('POSTGRES_PASSWORD'),
        'HOST': env.str('SQL_HOST'),
        'PORT': env.int('SQL_PORT'),
        'OPTIONS': {
            'sslmode': env.str('SSLMODE'),
            'sslrootcert': env.str('CA_SERTIFICATE_PATH'),
        }
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

# Multilanguage
LANGUAGES = [('en', _('English')), ('uz', _('Uzbek'))]
MODELTRANSLATION_DEFAULT_LANGUAGE = LANGUAGES[0][0]
MODELTRANSLATION_CUSTOM_FIELDS = 'CKEditor5Field',
MODELTRANSLATION_LANGUAGES = 'en', 'uz'

# Path to save locale files
LOCALE_PATHS = [
    join(BASE_DIR, env.str('TRANSLATES_PATH', 'locale'))
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    join(BASE_DIR, 'staticfiles'),
]

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = join(BASE_DIR, 'media')

# CORS Configuration
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Logs configuration
LOGGING = {
    'version': 1,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        }
    },
    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
        },
        'info': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/info.log'),
        },
        'warning': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/warning.log'),
        },
        'error': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/error.log'),
        },
        'critical': {
            'level': 'CRITICAL',
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/critical.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'info', 'warning', 'error', 'critical'],
            'propagate': True
        }
    }
}

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Only use these in production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django Debug Toolbar
INTERNAL_IPS = [
    "127.0.0.1", "localhost"
]

# Django Debug Toolbar Configuration
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TEMPLATE_CONTEXT': True,
    'ENABLE_STACKTRACES': True,
}

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]

# DRF Spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Visa Doctors API',
    'DESCRIPTION': 'API for Visa Doctors service',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    }
}

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    # 'PAGE_SIZE': 10,
}

# Jazzmin Settings
JAZZMIN_SETTINGS = {
    # Title on the login screen
    "site_title": "Visa Doctors Admin",

    # Title on the brand (19 chars max)
    "site_header": "Visa Doctors",

    # Square logo to use for your site
    "site_logo": None,

    # Welcome text on the login screen
    "welcome_sign": "Welcome to Visa Doctors",

    # Copyright on the footer
    "copyright": "Visa Doctors Ltd",

    # List of model admins to search from the search bar
    "search_model": ["auth.User", "auth.Group"],

    # Field name on user model that contains avatar image
    "user_avatar": None,

    ############
    # Top Menu #
    ############
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "auth.User"},
    ],

    #############
    # Side Menu #
    #############
    "show_sidebar": True,
    "navigation_expanded": True,

    # Custom icons for side menu apps/models
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
    },
}

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django.core.cache.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
        }
    }
} if not DEBUG else {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Cache middleware settings
if not DEBUG:
    CACHE_MIDDLEWARE_SECONDS = 60 * 15  # 15 minutes
    CACHE_MIDDLEWARE_KEY_PREFIX = 'visa_doctors'
