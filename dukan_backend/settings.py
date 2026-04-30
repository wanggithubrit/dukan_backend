import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

# ─────────────────────────────
# BASE
# ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Load env (for local dev)
load_dotenv()

# ─────────────────────────────
# SECURITY
# ─────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

DEBUG = False

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:19000",
    "http://10.194.216.149:8000",
]
# ─────────────────────────────
# APPS
# ─────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
]

# ─────────────────────────────
# MIDDLEWARE
# ─────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.PlanExpiryMiddleware",
]

ROOT_URLCONF = "dukan_backend.urls"

# ─────────────────────────────
# TEMPLATES
# ─────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
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

WSGI_APPLICATION = "dukan_backend.wsgi.application"

# ─────────────────────────────
# DATABASE (OK FOR NOW)
# ─────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ─────────────────────────────
# PASSWORD VALIDATION
# ─────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# ─────────────────────────────
# JWT
# ─────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
}

# ─────────────────────────────
# INTERNATIONAL
# ─────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True

# ─────────────────────────────
# STATIC FILES (IMPORTANT)
# ─────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# ─────────────────────────────
# MEDIA (TEMP)
# ─────────────────────────────
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ─────────────────────────────
# EMAIL
# ─────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# ─────────────────────────────
# RAZORPAY (SAFE)
# ─────────────────────────────
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# ─────────────────────────────
# REFERRAL
# ─────────────────────────────
REFERRAL_ENABLED = True
REFERRAL_REQUIRED = 3
REFERRAL_REWARD_DAYS = 30