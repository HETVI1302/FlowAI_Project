"""
FlowAI - Smart Traffic Management System
Django settings — Phase 1
GTU AI Hackathon — Smart Cities Category
"""

import os
from pathlib import Path
from datetime import timedelta

import environ

# ---------------------------------------------------------------------------
# BASE PATHS
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
# Reads a .env file at the project root (create one from .env.example)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# ---------------------------------------------------------------------------
# CORE / SECURITY
# ---------------------------------------------------------------------------
SECRET_KEY = env('SECRET_KEY', default='django-insecure-CHANGE-ME-BEFORE-DEPLOY')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# ---------------------------------------------------------------------------
# APPLICATION DEFINITION
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'django_filters',
]

LOCAL_APPS = [
    'accounts.apps.AccountsConfig',
    'dashboard.apps.DashboardConfig',
    'monitoring.apps.MonitoringConfig',
    'prediction.apps.PredictionConfig',
    'analytics.apps.AnalyticsConfig',
    'reports.apps.ReportsConfig',
    'signals_app.apps.SignalsAppConfig',
    'notifications.apps.NotificationsConfig',
    'api.apps.ApiConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = 'accounts.User'

# Session-based auth (server-rendered dashboard pages)
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'home'

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'flowai_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

# WSGI is kept for management commands / non-async deployments.
# ASGI is the primary entrypoint (see asgi.py) so Channels can serve
# both HTTP and WebSocket protocols behind Daphne/Uvicorn.
WSGI_APPLICATION = 'flowai_core.wsgi.application'
ASGI_APPLICATION = 'flowai_core.asgi.application'

# ---------------------------------------------------------------------------
# DATABASE — MySQL
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', default='flowai_db'),
        'USER': env('DB_USER', default='flowai_user'),
        'PASSWORD': env('DB_PASSWORD', default='changeme'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='3307'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ---------------------------------------------------------------------------
# REDIS — shared by the Channels layer and the Django cache
# ---------------------------------------------------------------------------
REDIS_HOST = env('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = env.int('REDIS_PORT', default=6379)
REDIS_URL = env('REDIS_URL', default=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

# ---------------------------------------------------------------------------
# DJANGO CHANNELS — WebSocket layer for the live dashboard + monitoring feed
# The YOLOv8 worker (built in a later phase) publishes detection events to
# this same Redis instance; consumers broadcast them to the frontend groups.
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, REDIS_PORT)],
            'capacity': 1500,  # headroom for burst frame-detection events
            'expiry': 10,
        },
    },
}

# ---------------------------------------------------------------------------
# TRAFFIC MONITORING — YOLOv8/OpenCV camera workers (monitoring.cv.pipeline)
# Each camera worker runs as its own process (see the `run_camera_worker`
# management command), never on the Django HTTP thread, and publishes
# results onto CHANNEL_LAYERS above for the live dashboard/monitoring pages.
# ---------------------------------------------------------------------------
YOLO_WEIGHTS_PATH = env('YOLO_WEIGHTS_PATH', default='yolov8n.pt')
YOLO_CONFIDENCE_THRESHOLD = env.float('YOLO_CONFIDENCE_THRESHOLD', default=0.4)
YOLO_DEVICE = env('YOLO_DEVICE', default='cpu')  # 'cpu', '0' (first CUDA GPU), etc.

# ---------------------------------------------------------------------------
# DJANGO REST FRAMEWORK + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {'anon': '30/minute', 'user': '120/minute'},
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:3000', 'http://127.0.0.1:8000'],
)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# SECURITY HARDENING
# ---------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 day

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC & MEDIA
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# LOGGING — useful once the CV worker starts streaming detections
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'flowai.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'monitoring': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
        'signals_app': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
}
