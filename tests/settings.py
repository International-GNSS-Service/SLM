from pathlib import Path
from split_settings.tools import include, optional
from slm.settings import unset
import os

from slm.settings import resource

BASE_DIR = Path(__file__).resolve().parent / "tmp"
os.makedirs(BASE_DIR, exist_ok=True)

ALLOWED_HOSTS = ["*"]

include(resource("slm.settings", "root.py"))
include(optional("./local.py"))

INSTALLED_APPS = ["django_extensions", *INSTALLED_APPS]

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGRES_DB", "slm_test"),
        "USER": os.environ.get("POSTGRES_USER", ""),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", ""),
        "PORT": os.environ.get("POSTGRES_PORT", ""),
    }
}

SLM_PRELOAD_SCHEMAS = False

# COMPRESS_ENABLED = False

unset("SECURE_SSL_REDIRECT")
unset("CSRF_COOKIE_SECURE")
unset("SESSION_COOKIE_SECURE")
unset("SECURE_REFERRER_POLICY")
unset("X_FRAME_OPTIONS")
MIDDLEWARE.remove("django.middleware.security.SecurityMiddleware")


WSGI_APPLICATION = "tests.wsgi.application"
DEBUG = True
