"""
Django settings for SLM.

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""

import platform
from pathlib import Path

from django.contrib.messages import constants as message_constants
from split_settings.tools import include, optional

from slm.settings import get_setting, set_default

DEBUG = get_setting("DEBUG", False)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = get_setting("BASE_DIR", Path(__file__).resolve().parent.parent)
SITE_DIR = get_setting("SITE_DIR", BASE_DIR)
DJANGO_DEBUG_TOOLBAR = get_setting("DJANGO_DEBUG_TOOLBAR", False)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

ALLOWED_HOSTS = get_setting("ALLOWED_HOSTS", [])
if ALLOWED_HOSTS:
    set_default("SERVER_EMAIL", f"noreply@{ALLOWED_HOSTS[0]}")

# Application definition

# django.contrib.___ gives us useful tools for authentication, etc.
INSTALLED_APPS = [
    # "slm.map",
    "slm",
    "crispy_forms",
    "crispy_bootstrap5",
    "ckeditor_uploader",
    "ckeditor",
    "polymorphic",
    "rest_framework",
    "rest_framework_gis",
    "render_static",
    "django_routines",
    "django_typer",
    "django_filters",
    "compressor",
    "widget_tweaks",
    #'django.contrib.postgres',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.gis",
    "allauth",
    "allauth.account",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)

# this statement was added during creation of custom user model
AUTH_USER_MODEL = "slm.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "slm.middleware.SetLastVisitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "slm.settings.urls"

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

# Following two statements added to assist with handling of static files
STATIC_URL = "/static/"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

set_default("SITE_ID", 1)

STATIC_ROOT = get_setting("STATIC_ROOT", SITE_DIR / "static")

COMPRESS_OFFLINE = True
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL


include("internationalization.py")
include("slm.py")
include("secrets.py")
include("logging.py")
include("templates.py")
include("static_templates.py")
include("routines.py")
include("auth.py")
include("rest.py")
include("debug.py")
include("uploads.py")
include("ckeditor.py")
include("security.py")
include("validation.py")

# will either be darwin, windows or linux
include(optional(f"./platform/{platform.system().lower()}.py"))


# Path(STATIC_ROOT).mkdir(parents=True, exist_ok=True)
# Path(MEDIA_ROOT).mkdir(parents=True, exist_ok=True)

MESSAGE_LEVEL = message_constants.DEBUG if DEBUG else message_constants.INFO
