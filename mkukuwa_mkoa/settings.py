import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Load .env into os.environ (does not override existing variables)."""
    env_file = BASE_DIR / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


_load_dotenv()

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-mkukuwa-mkoa-saas-key-2026')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

def _build_allowed_hosts():
    hosts = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]
    if not hosts:
        hosts = ['*']
    if DEBUG and '*' not in hosts:
        for suffix in (
            '.ngrok-free.dev',
            '.ngrok-free.app',
            '.ngrok.io',
            '.ngrok.app',
            'localhost',
            '127.0.0.1',
        ):
            if suffix not in hosts:
                hosts.append(suffix)
    return hosts


ALLOWED_HOSTS = _build_allowed_hosts()

# ngrok / reverse-proxy: trust HTTPS origin for CSRF; honor X-Forwarded-* from tunnel
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

_csrf_origins = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
_csrf_origins.extend(
    o.strip()
    for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
)
_ngrok_public = os.environ.get('NGROK_URL', '').strip().rstrip('/')
if _ngrok_public:
    _csrf_origins.append(_ngrok_public)
if DEBUG:
    _csrf_origins.extend([
        'https://*.ngrok-free.app',
        'https://*.ngrok-free.dev',
        'https://*.ngrok.io',
        'https://*.ngrok.app',
    ])
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_csrf_origins))

# Dev: localhost uses non-Secure cookies; ngrok HTTPS uses Secure (NgrokHttpsMiddleware)
if DEBUG:
    CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'apps.core',
    'apps.authentication',
    'apps.cooperative',
    'apps.members',
    'apps.payments',
    'apps.savings',
    'apps.shares',
    'apps.loans',
    'apps.accounting',
    'apps.governance',
    'apps.reporting',
    'apps.audit',
    'apps.notifications',
    'chatbot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.authentication.middleware.MustChangePasswordMiddleware',
    'apps.members.middleware.MemberLifecycleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.DatabaseResilienceMiddleware',
    'apps.core.middleware.CooperativeMiddleware',
    'apps.core.middleware.AuditLogMiddleware',
    'apps.core.middleware.NgrokHttpsMiddleware',
]

ROOT_URLCONF = 'mkukuwa_mkoa.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'builtins': [
                'apps.core.templatetags.locale_tags',
            ],
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.system_settings',
                'apps.core.context_processors.cooperative_info',
                'apps.core.context_processors.notifications_count',
                'apps.core.context_processors.language_preference',
                'apps.core.context_processors.database_mode',
                'apps.core.context_processors.rbac_permissions',
                'apps.core.context_processors.member_lifecycle',
            ],
        },
    },
]

WSGI_APPLICATION = 'mkukuwa_mkoa.wsgi.application'

# Database with auto-fallback to local SQLite when XAMPP/MySQL is down
from apps.core.db_resilience import build_database_config

DATABASES, ACTIVE_DB_MODE, DB_STATUS, MYSQL_PRIMARY_CONFIG = build_database_config(BASE_DIR)

# XAMPP ships MariaDB 10.4; Django 5.1+ requires 10.6+. Allow local dev on older MariaDB.
if (
    os.environ.get('DB_ENGINE') == 'django.db.backends.mysql'
    and os.environ.get('DB_ALLOW_OLD_MARIADB', 'true' if DEBUG else 'false').lower()
    in ('1', 'true', 'yes')
):
    from django.db.backends.base import base as _db_base

    _orig_version_check = _db_base.BaseDatabaseWrapper.check_database_version_supported

    def _allow_xampp_mariadb_version(self):
        if getattr(self, 'vendor', None) == 'mysql':
            return
        _orig_version_check(self)

    _db_base.BaseDatabaseWrapper.check_database_version_supported = _allow_xampp_mariadb_version

    # MariaDB < 10.5 has no INSERT ... RETURNING (Django 6 uses it on MariaDB by default)
    from django.db.backends.mysql import features as _mysql_features

    _mysql_features.DatabaseFeatures.can_return_columns_from_insert = property(
        lambda self: False
    )

AUTH_USER_MODEL = 'authentication.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en'
TIME_ZONE = 'Africa/Dar_es_Salaam'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('sw', 'Kiswahili'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/auth/login/'

SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Email Configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# SMS Configuration
SMS_API_KEY = os.environ.get('SMS_API_KEY', '')
SMS_SENDER_ID = os.environ.get('SMS_SENDER_ID', 'MKUUWA')

# Payment Gateways
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '')
MPESA_ENV = os.environ.get('MPESA_ENV', 'sandbox')

TIGO_API_KEY = os.environ.get('TIGO_API_KEY', '')
AIRTEL_API_KEY = os.environ.get('AIRTEL_API_KEY', '')

# OpenRouter AI (chatbot)
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
OPENROUTER_SITE_URL = os.environ.get('OPENROUTER_SITE_URL', 'http://127.0.0.1:8000')
OPENROUTER_SITE_NAME = os.environ.get('OPENROUTER_SITE_NAME', 'AMCOS AI')

# CORS — safe defaults for server-rendered app; enable API clients when needed
_cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if _cors_origins:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(',') if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
CORS_ALLOW_CREDENTIALS = True

# MGOWELO AMCOS — single cooperative (no registration code required)
MGOWELO_COOPERATIVE_CODE = os.environ.get('MGOWELO_COOPERATIVE_CODE', 'AMCOS001')
MEMBER_BOARD_APPROVALS_REQUIRED = int(os.environ.get('MEMBER_BOARD_APPROVALS_REQUIRED', '5'))
MEMBER_MIN_INITIAL_SHARES = int(os.environ.get('MEMBER_MIN_INITIAL_SHARES', '1'))
MEMBER_MAX_INITIAL_SHARES = int(os.environ.get('MEMBER_MAX_INITIAL_SHARES', '5'))

# Resilience / backup paths
BACKUP_ROOT = BASE_DIR / 'backups'
RUNTIME_DIR = BASE_DIR / 'runtime'

# Cache — LocMem default; set CACHE_BACKEND=redis and REDIS_URL for production scale
_cache_backend = os.environ.get('CACHE_BACKEND', 'locmem').lower()
if _cache_backend == 'redis':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
            'KEY_PREFIX': os.environ.get('CACHE_KEY_PREFIX', 'amcos'),
            'TIMEOUT': int(os.environ.get('CACHE_TIMEOUT', '300')),
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'amcos-default',
        }
    }
