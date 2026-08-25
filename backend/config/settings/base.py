from pathlib import Path

from decouple import config, Csv
from datetime import timedelta
import environ

env = environ.Env()


LIPILA_ENVIRONMENT = env(
    "LIPILA_ENVIRONMENT",
    default="sandbox",
)

LIPILA_SANDBOX_BASE_URL = env(
    "LIPILA_SANDBOX_BASE_URL",
    default="https://api.lipila.dev",
)

LIPILA_PRODUCTION_BASE_URL = env(
    "LIPILA_PRODUCTION_BASE_URL",
    default="https://blz.lipila.io",
)

LIPILA_SANDBOX_API_KEY = env(
    "LIPILA_SANDBOX_API_KEY",
    default="",
)

LIPILA_PRODUCTION_API_KEY = env(
    "LIPILA_PRODUCTION_API_KEY",
    default="",
)

LIPILA_WEBHOOK_SECRET = env(
    "LIPILA_WEBHOOK_SECRET",
    default="",
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


SECRET_KEY = config("SECRET_KEY")

DEBUG = config(
    "DEBUG",
    default=False,
    cast=bool,
)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=Csv(),
)

# Full scheme+host origins allowed to make unsafe (POST/PUT/etc) requests —
# needed for django-admin logins in production, where Caddy terminates TLS
# and this is the https:// address the browser actually sees. See
# SECURE_PROXY_SSL_HEADER below for the other half of this.
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="",
    cast=Csv(),
)

# The publicly reachable origin for this backend — used to build the
# webhook callback URL sent to Lipila. Deliberately NOT derived from the
# incoming request's Host header: in local dev the browser talks to the
# backend directly on localhost, bypassing whatever tunnel (ngrok, etc.)
# actually exposes it to the internet, so request.build_absolute_uri()
# would hand Lipila an unreachable localhost URL. Leave blank in a normal
# single-domain deployment (prod) where the request's own host is already
# correct.
PUBLIC_BASE_URL = config(
    "PUBLIC_BASE_URL",
    default="",
).rstrip("/")

# The public registration site's URL — used for links inside outgoing
# emails (e.g. the "track your registration" button). Separate from
# PUBLIC_BASE_URL, which points at this backend, not the frontend.
PUBLIC_SITE_URL = config(
    "PUBLIC_SITE_URL",
    default="",
).rstrip("/")

# Shown in the footer of outgoing emails.
EVENT_CONTACT_PHONE = config(
    "EVENT_CONTACT_PHONE",
    default="",
)

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",

    # Platform
    "apps.common",
    "apps.accounts",
    "apps.organizations",
    "apps.events",
    "apps.participants",
    "apps.registrations",
    "apps.payments",
    "apps.payment_providers",
    "apps.notifications",
]

AUTH_USER_MODEL = "accounts.User"



MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=30
    ),

    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=7
    ),

    "ROTATE_REFRESH_TOKENS": True,

    "BLACKLIST_AFTER_ROTATION": True,

    "UPDATE_LAST_LOGIN": True,

    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),
}

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
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config(
            "DB_PORT",
            default="5432",
        ),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Lusaka"

USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Safer default: endpoints must opt IN to being public (AllowAny) rather
    # than opt out of requiring auth. Public registration/payment endpoints
    # already set permission_classes = [AllowAny] explicitly.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 25,
}


# CORS_ALLOWED_ORIGINS = config(
#     "CORS_ALLOWED_ORIGINS",
#     default="http://localhost:5173",
#     cast=Csv,
# )

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://localhost:5174",
    cast=Csv(),
)

# Any subdomain of copperbeltmarathon2026.com (bare domain, www, and any
# custom subdomain — main-admin, view, and whatever gets added later) is
# trusted automatically, so a new Vercel subdomain never needs a backend
# env var change/redeploy to be able to call this API.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://([a-z0-9-]+\.)*copperbeltmarathon2026\.com$",
]

REDIS_URL = config(
    "REDIS_URL",
    default="redis://localhost:6379/0",
)


CELERY_BROKER_URL = REDIS_URL

CELERY_RESULT_BACKEND = REDIS_URL

CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "Africa/Lusaka"

# Set to True to run notification/webhook side-effects synchronously
# instead of via Celery. Useful for a fast "deploy today" setup where a
# Celery worker/Redis isn't guaranteed to be running yet.
CELERY_TASK_ALWAYS_EAGER = config(
    "CELERY_TASK_ALWAYS_EAGER",
    default=True,
    cast=bool,
)


# ---------------------------------------------------------------------------
# Email (registration + payment notifications)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = config(
    "EMAIL_HOST",
    default="smtp.gmail.com",
)

EMAIL_PORT = config(
    "EMAIL_PORT",
    default=587,
    cast=int,
)

EMAIL_USE_TLS = config(
    "EMAIL_USE_TLS",
    default=True,
    cast=bool,
)

EMAIL_HOST_USER = config(
    "EMAIL_HOST_USER",
    default="",
)

EMAIL_HOST_PASSWORD = config(
    "EMAIL_HOST_PASSWORD",
    default="",
)

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default=EMAIL_HOST_USER,
)


# ---------------------------------------------------------------------------
# SMS (pluggable — no provider wired up yet, see apps/notifications/sms.py)
# ---------------------------------------------------------------------------
SMS_BACKEND = config(
    "SMS_BACKEND",
    # "console" just logs the message instead of sending it, so the rest
    # of the notification pipeline (and the admin's notification log)
    # works end-to-end before a real SMS provider is wired up.
    default="console",
)

SMS_SENDER_ID = config(
    "SMS_SENDER_ID",
    default="CBTMarathon",
)

# Africa's Talking is the most common SMS provider for Zambia/Zambia-adjacent
# apps, so the client is stubbed for it — fill these in and set
# SMS_BACKEND=africastalking once you have an account.
AFRICASTALKING_USERNAME = config(
    "AFRICASTALKING_USERNAME",
    default="",
)

AFRICASTALKING_API_KEY = config(
    "AFRICASTALKING_API_KEY",
    default="",
)


# ---------------------------------------------------------------------------
# Lipila (payments)
# ---------------------------------------------------------------------------
# NOTE: Lipila's public docs describe two API surfaces (a legacy
# "collections" API under /api/v1/collections/... using an x-api-key
# header, and a newer "transactions" API under /transactions/... using a
# Bearer secret key). The client below is built against the x-api-key /
# /api/v1/... style already used elsewhere in this project. If your Lipila
# dashboard issued you a "secret key" instead of an "x-api-key" style key,
# or your account is on the newer /transactions/ surface, update
# apps/payments/providers/lipila/client.py and the endpoint paths below to
# match what's shown in your Lipila merchant dashboard.
LIPILA_DISBURSEMENT_ENDPOINT = config(
    "LIPILA_DISBURSEMENT_ENDPOINT",
    default="/api/v1/disbursements/mobile-money",
)

LIPILA_BALANCE_ENDPOINT = config(
    "LIPILA_BALANCE_ENDPOINT",
    default="/api/v1/merchants/balance",
)


# ---------------------------------------------------------------------------
# This event (single-event deployment)
# ---------------------------------------------------------------------------
# The frontend and seed command both key off this event ID. Set it after
# running `python manage.py seed_copperbelt_marathon`, which prints the
# event ID it created.
CURRENT_EVENT_ID = config(
    "CURRENT_EVENT_ID",
    default="",
)


# ---------------------------------------------------------------------------
# Bank account (for the "Bank Transfer" payment method)
# ---------------------------------------------------------------------------
# Shown to runners who choose to pay by bank transfer instead of mobile
# money — kept server-side (rather than hardcoded in the frontend) so it
# can be corrected/rotated without a frontend deploy.
BANK_ACCOUNT_DETAILS = {
    "bank_name": config("BANK_NAME", default=""),
    "account_name": config("BANK_ACCOUNT_NAME", default=""),
    "account_number": config("BANK_ACCOUNT_NUMBER", default=""),
    "branch": config("BANK_BRANCH", default=""),
    "sort_code": config("BANK_SORT_CODE", default=""),
    "swift_code": config("BANK_SWIFT_CODE", default=""),
}