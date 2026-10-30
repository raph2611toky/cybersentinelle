"""Configuration SAFIDIKO : diffusion publique et édition autorisée."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEBUG = os.getenv("DEBUG", "true").lower() in {"true", "1", "yes"}
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-only-local-debug")
if not DEBUG and (
    not os.getenv("SECRET_KEY") or SECRET_KEY.startswith("django-insecure")
):
    raise RuntimeError("SECRET_KEY forte et explicite requise en production")
ALLOWED_HOSTS = [
    x.strip()
    for x in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost" if DEBUG else "").split(
        ","
    )
    if x.strip()
]
if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS obligatoire en production")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_yasg",
    "apps.core.apps.CoreConfig",
    "apps.content_api.apps.ContentApiConfig",
    "apps.resources.apps.ResourcesConfig",
    "apps.pedagogie.apps.PedagogieConfig",
    "apps.publication.apps.PublicationConfig",
    "apps.media_studio.apps.MediaStudioConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "helpers.api.middleware.JsonErrorMiddleware",
    "helpers.api.middleware.PrivacyHeadersMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    required = ["MYSQL_NAME", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_HOST"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError("Variables MySQL absentes: " + ", ".join(missing))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ["MYSQL_NAME"],
            "USER": os.environ["MYSQL_USER"],
            "PASSWORD": os.environ["MYSQL_PASSWORD"],
            "HOST": os.environ["MYSQL_HOST"],
            "PORT": os.getenv("MYSQL_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            "CONN_MAX_AGE": 60,
        }
    }
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Indian/Antananarivo"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static_assets"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication"
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "helpers.api.exceptions.json_exception_handler",
}
CORS_ALLOWED_ORIGINS = [
    x.strip()
    for x in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173" if DEBUG else "",
    ).split(",")
    if x.strip()
]
CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_METHODS = ["GET", "HEAD", "OPTIONS"]
CORS_ALLOW_HEADERS = [
    "accept",
    "content-type",
    "if-none-match",
    "origin",
    "x-csrftoken",
]
SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": True,
    "SECURITY_DEFINITIONS": {
        "CSRF": {
            "type": "apiKey",
            "name": "X-CSRFToken",
            "in": "header",
            "description": "Le cookie de la protection Swagger ne donne pas de droits éditoriaux ; les écritures exigent une session staff Django et CSRF.",
        }
    },
    "DEFAULT_INFO": "helpers.api.swagger.api_info",
}
SWAGGER_ENABLED = DEBUG or os.getenv("SWAGGER_ENABLED", "false").lower() == "true"
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# N'activer cet en-tête que derrière un reverse-proxy de confiance correctement configuré.
if not DEBUG and os.getenv("TRUST_PROXY_SSL_HEADER", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CONTENT_ROOT = Path(os.getenv("CONTENT_ROOT", str(BASE_DIR / "content"))).resolve()
RELEASES_ROOT = CONTENT_ROOT / "releases"
# Toujours servir les releases validées : aucun fallback vers les brouillons en base.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"safe": {"format": "%(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe"}},
    "loggers": {
        "safidiko": {"handlers": ["console"], "level": "INFO", "propagate": False}
    },
}

MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))).resolve()
if not MEDIA_URL.endswith("/"):
    raise RuntimeError("MEDIA_URL doit finir par / (exemple : /media/)")
SWAGGER_PASSWORD = os.getenv("SWAGGER_PASSWORD", "")
SWAGGER_COOKIE_MAX_AGE = int(os.getenv("SWAGGER_COOKIE_MAX_AGE", "3600"))
if SWAGGER_COOKIE_MAX_AGE < 60 or SWAGGER_COOKIE_MAX_AGE > 86400:
    raise RuntimeError("SWAGGER_COOKIE_MAX_AGE doit être compris entre 60 et 86400 secondes")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SWAGGER_USE_COMPAT_RENDERERS = False

FORMS_URLFIELD_ASSUME_HTTPS = True


# Studio média - fichiers bruts uniquement dans un emplacement PRIVÉ, jamais exposé par /media/.
STUDIO_PRIVATE_ROOT = Path(os.getenv('STUDIO_PRIVATE_ROOT', str(BASE_DIR / 'private_media'))).resolve()
if STUDIO_PRIVATE_ROOT.is_relative_to(MEDIA_ROOT):
    raise RuntimeError('STUDIO_PRIVATE_ROOT doit être distinct de MEDIA_ROOT exposé en développement')
STUDIO_MAX_UPLOAD_BYTES = int(os.getenv('STUDIO_MAX_UPLOAD_MB', '120')) * 1024 * 1024
STUDIO_MAX_MEDIA_SECONDS = int(os.getenv('STUDIO_MAX_MEDIA_SECONDS', '240'))
STUDIO_MAX_OUTPUT_BYTES = 150 * 1024 * 1024
STUDIO_MAX_TTS_RESULT_BYTES = 20 * 1024 * 1024
STUDIO_MAX_TTS_CHARS = min(int(os.getenv('STUDIO_MAX_TTS_CHARS', '1200')), 2500)
STUDIO_TTS_DAILY_LIMIT = min(int(os.getenv('STUDIO_TTS_DAILY_LIMIT', '12')), 100)
STUDIO_TTS_PROVIDERS = {x.strip().upper() for x in os.getenv('STUDIO_TTS_PROVIDERS', 'GEMINI,ELEVENLABS').split(',') if x.strip()}
STUDIO_PROVIDER_TIMEOUT = 65
STUDIO_RENDER_TIMEOUT = 180

# Une file de travail est nécessaire pour ne pas bloquer le serveur HTTP.
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
