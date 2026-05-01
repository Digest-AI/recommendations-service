import os
from pathlib import Path

import dotenv
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

dotenv.load_dotenv(BASE_DIR / ".env")

# Secrets

SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.environ.get("ENVIRONMENT") != "production"

HOST = os.environ.get("HOST")
SELF_URL = f"http{'' if DEBUG else 's'}://{HOST}"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS").split(",")
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS").split(",")

SERVICE_ID = os.environ.get("SERVICE_ID")
SERVICE_SECRET = os.environ.get("SERVICE_SECRET")

# Recommendations
# Source of event data. "in_memory" reads seed_events.json from
# api/gateways/. Switch to "http" once the parser API is ready and
# implement HttpEventGateway alongside the in-memory one.
EVENT_GATEWAY = os.environ.get("EVENT_GATEWAY", "in_memory")
EVENTS_API_BASE_URL = os.environ.get("EVENTS_API_BASE_URL", "")

# Daily refresh job
DAILY_REFRESH_HOUR = int(os.environ.get("DAILY_REFRESH_HOUR", 3))
DAILY_REFRESH_MINUTE = int(os.environ.get("DAILY_REFRESH_MINUTE", 0))
DAILY_REC_LIMIT = int(os.environ.get("DAILY_REC_LIMIT", 20))
RUN_SCHEDULER = os.environ.get("RUN_SCHEDULER", "false").lower() == "true"

# Telegram bot push
TG_SERVICE_BASE_URL = os.environ.get("TG_SERVICE_BASE_URL", "")
TG_SERVICE_SECRET = os.environ.get("TG_SERVICE_SECRET", "")
TG_SERVICE_TIMEOUT = float(os.environ.get("TG_SERVICE_TIMEOUT", 10.0))
TG_SERVICE_RETRIES = int(os.environ.get("TG_SERVICE_RETRIES", 2))
TG_NOTIFY_HOUR = int(os.environ.get("TG_NOTIFY_HOUR", 10))
TG_NOTIFY_MINUTE = int(os.environ.get("TG_NOTIFY_MINUTE", 0))

# User service (for Bearer-token validation on user-facing endpoints)
USER_SERVICE_BASE_URL = os.environ.get("USER_SERVICE_BASE_URL", "")
USER_SERVICE_TIMEOUT = float(os.environ.get("USER_SERVICE_TIMEOUT", 5.0))


# Installed Apps

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "api.apps.ApiConfig",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "django_apscheduler",
]

# Middleware

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "utils.i18n_middleware.I18nMiddleware",
]

# Application

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# DRF

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "utils.renderers.CamelCaseJSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "utils.parsers.CamelCaseJSONParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "utils.exception_handler.exception_handler",
}

# DRF Spectacular

SPECTACULAR_SETTINGS = {
    "TITLE": os.environ.get("SERVICE_ID").replace("-service", "").title() + " API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": True,
}

# Databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Caches

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Static and Media

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

PUBLIC_URL = "/public/"
PUBLIC_ROOT = BASE_DIR / "public"

# Security

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_PROXY_SSL_HEADER: tuple[str, str] | None = None
SECURE_SSL_REDIRECT = False

# Production security (applied automatically if ENVIRONMENT=production)
if os.environ.get("ENVIRONMENT") == "production":
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )
    SECURE_SSL_REDIRECT = True

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "cache-control",
    "pragma",
    "expires",
]

# Misc

LANGUAGE_CODE = "en-us"
SUPPORTED_LANGUAGES = ("en", "ru", "ro")
DEFAULT_LANGUAGE = "en"

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
