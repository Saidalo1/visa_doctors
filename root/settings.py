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

    # Third party apps
    'adminsortable2',
    'corsheaders',
    'debug_toolbar',
    'django_ckeditor_5',
    'drf_spectacular',
    'import_export',
    'mptt',
    'rest_framework',
    'safedelete',

    # Local apps
    'app.apps.AppConfig',
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

# CKEditor Configuration
customColorPalette = [
    {'color': 'hsl(4, 90%, 58%)', 'label': 'Red'},
    {'color': 'hsl(340, 82%, 52%)', 'label': 'Pink'},
    {'color': 'hsl(291, 64%, 42%)', 'label': 'Purple'},
    {'color': 'hsl(262, 52%, 47%)', 'label': 'Deep Purple'},
    {'color': 'hsl(231, 48%, 48%)', 'label': 'Indigo'},
    {'color': 'hsl(207, 90%, 54%)', 'label': 'Blue'},
    {'color': 'hsl(199, 98%, 48%)', 'label': 'Light Blue'},
    {'color': 'hsl(187, 100%, 42%)', 'label': 'Cyan'},
    {'color': 'hsl(174, 100%, 29%)', 'label': 'Teal'},
    {'color': 'hsl(122, 39%, 49%)', 'label': 'Green'},
    {'color': 'hsl(88, 50%, 53%)', 'label': 'Light Green'},
    {'color': 'hsl(66, 70%, 54%)', 'label': 'Lime'},
    {'color': 'hsl(49, 98%, 60%)', 'label': 'Yellow'},
    {'color': 'hsl(45, 100%, 51%)', 'label': 'Amber'},
    {'color': 'hsl(36, 100%, 50%)', 'label': 'Orange'},
    {'color': 'hsl(14, 91%, 54%)', 'label': 'Deep Orange'},
    {'color': 'hsl(15, 25%, 34%)', 'label': 'Brown'},
    {'color': 'hsl(0, 0%, 62%)', 'label': 'Grey'},
    {'color': 'hsl(200, 18%, 46%)', 'label': 'Blue Grey'},
    {'color': 'hsl(200, 18%, 100%)', 'label': 'White'},
]

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                   'bulletedList', 'numberedList', 'blockQuote', '|',
                   'imageUpload', 'insertTable', 'mediaEmbed', '|',
                   'undo', 'redo', '|', 'sourceEditing'],
        'heading': {
            'options': [
                {'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph'},
                {'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1'},
                {'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2'},
                {'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3'}
            ]
        },
        'image': {
            'toolbar': ['imageTextAlternative', 'imageStyle:full', 'imageStyle:side']
        },
        'table': {
            'contentToolbar': ['tableColumn', 'tableRow', 'mergeTableCells']
        },
        'fontSize': {
            'options': [9, 11, 13, 'default', 17, 19, 21]
        },
        'color': {
            'colors': customColorPalette,
            'columns': 5,
        },
        'alignment': {
            'options': ['left', 'center', 'right', 'justify']
        },
        'language': {
            'ui': 'en',
            'content': 'en'
        },
        'height': '400px',
        'width': '100%',
    }
}

CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
CKEDITOR_5_UPLOAD_PATH = "uploads/ckeditor/"
# CKEDITOR_5_CUSTOM_CSS = "path-to-custom.css"  # Optional
CKEDITOR_5_CONFIGS_PROFILE = 'default'  # The profile to use as default

CKEDITOR_5_UPLOAD_FILE_TYPES = "image/jpeg,image/png,image/gif"
CKEDITOR_5_MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB max file size

# Logs configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'info_file': {
            'level': 'INFO',
            'filters': ['require_debug_false'],
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/info.log'),
            'formatter': 'verbose',
        },
        'warning_file': {
            'level': 'WARNING',
            'filters': ['require_debug_false'],
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/warning.log'),
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/error.log'),
            'formatter': 'verbose',
        },
        'critical_file': {
            'level': 'CRITICAL',
            'filters': ['require_debug_false'],
            'class': 'logging.FileHandler',
            'filename': join(BASE_DIR, 'logs/critical.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'info_file', 'warning_file', 'error_file', 'critical_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
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
        "users.User": "fas fa-user",
        "auth.Group": "fas fa-users",
        "admin.LogEntry": "fas fa-file",
        
        # Pages
        "app.about": "fas fa-info-circle",
        "app.abouthighlight": "fas fa-star",
        "app.visatype": "fas fa-passport",
        "app.visadocument": "fas fa-file-alt",
        "app.resultcategory": "fas fa-folder",
        "app.result": "fas fa-check-circle",
        "app.contactinfo": "fas fa-address-book",
        
        # Survey
        "app.question": "fas fa-question-circle",
        "app.answeroption": "fas fa-list",
        "app.surveysubmission": "fas fa-paper-plane",
        "app.response": "fas fa-reply",
    },
    
    # Add support dark theme
    "show_ui_builder": True,
    "dark_mode_theme": "darkly",
    "custom_css": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "related_modal_active": True,
    "custom_links": {},
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-arrow-circle-right",
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [],
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
