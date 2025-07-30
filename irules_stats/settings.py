import logging
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from rest_framework import authentication

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
if os.getenv('DEBUG', default=False) in ['True', 'true', '1', True]:
    DEBUG = True
else:
    DEBUG = False


ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1').split(' ')
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1').split(' ')
DOMAIN = os.getenv('DOMAIN')
API_DOMAIN = os.getenv('API_DOMAIN')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 'main.apps.MainConfig',
    'park.apps.ParkConfig',

    'rest_framework',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'debug_toolbar',
    'phonenumber_field',
    'django_celery_beat',

    'drf_yasg',
    'flower',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'irules_stats.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'irules_stats.wsgi.application'
ASGI_APPLICATION = 'irules_stats.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Rest faramework
DEFAULT_RENDERER_CLASSES = [
    'rest_framework.renderers.JSONRenderer',
]

DEFAULT_AUTHENTICATION_CLASSES = [
    'rest_framework_simplejwt.authentication.JWTAuthentication'
]

authentication.TokenAuthentication.keyword = 'Bearer'

if DEBUG:
    DEFAULT_RENDERER_CLASSES = DEFAULT_RENDERER_CLASSES + [
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]

    DEFAULT_AUTHENTICATION_CLASSES = DEFAULT_AUTHENTICATION_CLASSES + [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]

    INTERNAL_IPS = [
        '127.0.0.1',
    ]

    BOT_TOKEN = os.getenv('BOT_TOKEN_DEV')
    HOST = 'tuenakopob.beget.app'

else:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    HOST = os.getenv('HOST')

# БД
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('PASSWORD'),
        'HOST': HOST,
        'PORT': os.getenv('PORT'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': DEFAULT_AUTHENTICATION_CLASSES,

    'PAGE_SIZE': os.getenv('PAGE_SIZE'),
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DATETIME_FORMAT': "%Y-%m-%d %H:%M:%S",
    'DEFAULT_RENDERER_CLASSES': DEFAULT_RENDERER_CLASSES,
}

# OTP
# название приложения в яндекс ключ
OTP_TOTP_ISSUER = 'iruler'
PYOTP_TOTP_NAME = 'iruler'

# Интегратор
INTEGRATOR_ID = os.getenv('INTEGRATOR_ID')
INTEGRATOR_API_KEY = os.getenv('INTEGRATOR_API_KEY')

# НАСТРОЙКИ
# количество цифр в одноразовом пароле для входа
COUNT_CHARS_IN_PASSWORD = os.getenv('COUNT_CHARS_IN_PASSWORD')


# REDIS
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_USERNAME = os.getenv('REDIS_USERNAME')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

REDIS_SERVER_0 = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'


# CELERY
CELERY_BROKER_URL = REDIS_SERVER_0
CELERY_RESULT_BACKEND = REDIS_SERVER_0
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# LOGGER
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', 'DEBUG')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'django_format': {
            'format': '{levelname} {asctime} {name} {processName} {funcName} {lineno} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {name} {funcName} {lineno} {message}',
            'style': '{',
        }
    },
    'filters': {
        # Фильтр для уровня INFO
        'info_only': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: record.levelno == logging.INFO,
        },
        # Фильтр для уровня WARNING
        'warning_only': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: record.levelno == logging.WARNING,
        },
    },
    'handlers': {
        'console': {
            'level': LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_info': {
            'level': 'INFO',  # Логи уровня INFO и ниже
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'info.log',
            'maxBytes': 1024 * 1024 * 3,
            'backupCount': 2,
            'formatter': 'django_format',
            'filters': ['info_only'],  # Применяем фильтр
        },
        'file_warning': {
            'level': 'WARNING',  # Логи уровня WARNING и ниже (до ERROR)
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'warning.log',
            'maxBytes': 1024 * 1024 * 3,
            'backupCount': 2,
            'formatter': 'django_format',
            'filters': ['warning_only'],  # Применяем фильтр
        },
        'file_error': {
            'level': 'ERROR',  # Логи уровня ERROR и выше
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'error.log',
            'maxBytes': 1024 * 1024 * 3,
            'backupCount': 2,
            'formatter': 'django_format',
        },
        'file_django_error': {
            'level': 'ERROR',  # Ошибки уровня ERROR для django
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'django_error.log',
            'maxBytes': 1024 * 1024 * 3,
            'backupCount': 2,
            'formatter': 'django_format',
        },
        'file_db_error': {
            'level': 'ERROR',  # Ошибки уровня ERROR для django.db.backends
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'db_error.log',
            'maxBytes': 1024 * 1024 * 3,
            'backupCount': 2,
            'formatter': 'django_format',
        },
        'celery': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'celery.log',
            'maxBytes': 1024 * 1024 * 3,
            'backupCount': 2,
            'formatter': 'django_format',
        }
    },
    'root': {
        'level': 'ERROR',
        'handlers': ['console', 'file_info', 'file_warning', 'file_error'],
    },
    'loggers': {
        'django': {
            'level': 'INFO',
            'handlers': ['console', 'file_info', 'file_django_error'],  # Добавлен file_django_error
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'ERROR',  # Для ошибок базы данных
            'handlers': ['file_db_error'],  # Логи ошибок пишем в db_error.log
            'propagate': False,
        },
        'notification': {
            'handlers': ['celery', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['celery'],
            'level': 'ERROR',
            'propagate': False,
        },
        'flower': {
            'handlers': ['celery'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}


# Настройки авторизации в документации
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Basic': {
            'type': 'basic'
        },
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'swagger_fake_view': False
}
