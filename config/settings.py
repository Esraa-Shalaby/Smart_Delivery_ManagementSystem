"""
Django settings for Smart Delivery & Logistics Management System.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# ------------------------------------------------------------------
# Base directory & environment variables
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def get_env(key, default=None, required=False):
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def get_env_bool(key, default=False):
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def get_env_list(key, default=""):
    value = os.getenv(key, default)
    return [item.strip() for item in value.split(",") if item.strip()]


# ------------------------------------------------------------------
# Security
# ------------------------------------------------------------------
SECRET_KEY = get_env("DJANGO_SECRET_KEY", required=True)

DEBUG = get_env_bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = get_env_list("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1")

# ------------------------------------------------------------------
# Application definition
# ------------------------------------------------------------------


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.shipments",
    "apps.drivers",
    "apps.warehouses",
    "apps.payments",
    "apps.complaints",
    "apps.notifications",
    "apps.analytics",
    "apps.ai_agent",
    "apps.common",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ------------------------------------------------------------------
# Database (PostgreSQL)
# ------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_env("DB_NAME", required=True),
        "USER": get_env("DB_USER", required=True),
        "PASSWORD": get_env("DB_PASSWORD", required=True),
        "HOST": get_env("DB_HOST", default="localhost"),
        "PORT": get_env("DB_PORT", default="5432"),
    }
}

# ------------------------------------------------------------------
# Custom user model
# ------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# ------------------------------------------------------------------
# Password validation
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------
# Django REST Framework
# ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ------------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = get_env("DJANGO_TIME_ZONE", default="Africa/Cairo")
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Static & media files
# ------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------------------------------------------
# Default primary key field type
# ------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------
# Security hardening (effective when DEBUG = False)
# ------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = get_env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True