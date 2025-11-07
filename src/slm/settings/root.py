"""
Django settings for SLM.

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""

import os
import platform
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from split_settings.tools import include, optional

from slm.settings import env as settings_environment
from slm.settings import (
    get_setting,
    resource,
    set_default,
    slm_path_mk_dirs_must_exist,
    slm_path_must_exist,
)

env = settings_environment()

DEBUG = env("DEBUG", default=get_setting("DEBUG", False))

# manage.py will set this to true if django has been loaded to run a
# management command - this mostly influences logging
SLM_MANAGEMENT_MODE = env.parse_value(
    os.environ.get("SLM_MANAGEMENT_FLAG", False), bool
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(
    env(
        "BASE_DIR",
        str,
        default=get_setting("BASE_DIR", env.NOTSET),
    )
).resolve()

if not BASE_DIR.is_dir():
    raise ImproperlyConfigured(f"BASE_DIR: {BASE_DIR} is not a directory.")

SLM_DEBUG_TOOLBAR = env(
    "SLM_DEBUG_TOOLBAR", bool, default=get_setting("DJANGO_DEBUG_TOOLBAR", DEBUG)
)
SLM_SECURITY_DEFAULTS = env(
    "SLM_SECURITY_DEFAULTS",
    bool,
    default=get_setting("SLM_SECURITY_DEFAULTS", not DEBUG),
)

SLM_IGS_VALIDATION = env(
    "SLM_IGS_VALIDATION", bool, default=get_setting("SLM_IGS_VALIDATION", True)
)

SLM_ADMIN_MAP = env("SLM_ADMIN_MAP", bool, default=get_setting("SLM_ADMIN_MAP", True))
SLM_FILE_VIEWS = env(
    "SLM_FILE_VIEWS", bool, default=get_setting("SLM_FILE_VIEWS", True)
)
SLM_SITE_NAME = env("SLM_SITE_NAME", str, default=get_setting("SLM_SITE_NAME", ""))
SLM_ORG_NAME = env("SLM_ORG_NAME", str, default=get_setting("SLM_ORG_NAME", "SLM"))

SLM_FILE_VIEW_FORMATS = env(
    "SLM_FILE_VIEW_FORMATS",
    list,
    default=get_setting("SLM_FILE_VIEW_FORMATS", ["ASCII_9CHAR"]),
)
SLM_FILE_VIEW_FORMATS = env(
    "SLM_FILE_VIEW_FORMATS",
    list,
    default=get_setting("SLM_FILE_VIEW_FORMATS", ["ASCII_9CHAR"]),
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=get_setting(
        "ALLOWED_HOSTS",
        ["localhost", "127.0.0.1", "[::1]"]
        if DEBUG
        else ([SLM_SITE_NAME] if SLM_SITE_NAME else []),
    ),
)
if not SLM_SITE_NAME and ALLOWED_HOSTS:
    SLM_SITE_NAME = ALLOWED_HOSTS[0]

INSTALLED_APPS = set_default(
    "INSTALLED_APPS",
    [
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
        "hijack",
        "hijack.contrib.admin",
        "django.contrib.postgres",
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
    ],
)

if SLM_ADMIN_MAP:
    INSTALLED_APPS.insert(0, "slm.map")
if SLM_FILE_VIEWS:
    INSTALLED_APPS.insert(0, "slm.file_views")


SLM_DATABASE = env(
    "SLM_DATABASE", str, default=set_default("SLM_DATABASE", "postgis:///slm")
)
DATABASES = set_default("DATABASES", {})
DATABASES["default"] = {
    "ATOMIC_REQUESTS": True,
    **DATABASES.get("default", {}),
    **env.db_url_config(
        SLM_DATABASE,
        engine="django.contrib.gis.db.backends.postgis",  # must have postgis!
    ),
}

SLM_CACHE = env("SLM_CACHE", str, default=set_default("SLM_CACHE", "locmemcache://"))
CACHES = set_default("CACHES", {})
CACHES["default"] = {**env.cache_url_config(SLM_CACHE), **CACHES.get("default", {})}

# do not show django hijack window - we use our own menu
HIJACK_INSERT_BEFORE = None

set_default("CRISPY_ALLOWED_TEMPLATE_PACKS", "bootstrap5")
set_default("CRISPY_TEMPLATE_PACK", "bootstrap5")

set_default(
    "STATICFILES_FINDERS",
    (
        "django.contrib.staticfiles.finders.FileSystemFinder",
        "django.contrib.staticfiles.finders.AppDirectoriesFinder",
        "compressor.finders.CompressorFinder",
    ),
)

# this statement was added during creation of custom user model
set_default("AUTH_USER_MODEL", "slm.User")

set_default(
    "MIDDLEWARE",
    [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "allauth.account.middleware.AccountMiddleware",
        "slm.middleware.SetLastVisitMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "hijack.middleware.HijackUserMiddleware",
    ],
)

set_default("ROOT_URLCONF", "slm.settings.urls")

# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

set_default(
    "AUTH_PASSWORD_VALIDATORS",
    [
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
    ],
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

# Following two statements added to assist with handling of static files
set_default("STATIC_URL", "/static/")

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

set_default("DEFAULT_AUTO_FIELD", "django.db.models.BigAutoField")

set_default("SITE_ID", 1)

STATIC_ROOT = env(
    "STATIC_ROOT",
    slm_path_mk_dirs_must_exist,
    default=get_setting("STATIC_ROOT", BASE_DIR / "static"),
)

env = settings_environment()

GDAL_LIBRARY_PATH = env(
    "GDAL_LIBRARY_PATH",
    slm_path_must_exist,
    default=get_setting("GDAL_LIBRARY_PATH", None),
)
GEOS_LIBRARY_PATH = env(
    "GEOS_LIBRARY_PATH",
    slm_path_must_exist,
    default=get_setting("GEOS_LIBRARY_PATH", None),
)

include("slm.py")
include("emails.py")
include("internationalization.py")
include("secrets.py")
include("logging.py")
include("templates.py")
include("static_templates.py")
include("auth.py")
include("rest.py")
include("debug.py")
include("uploads.py")
include("ckeditor.py")
if SLM_SECURITY_DEFAULTS:
    include("security.py")
if SLM_IGS_VALIDATION:
    include("validation.py")
include("assets.py")
include("routines.py")

# will either be darwin, windows or linux
include(optional(f"./platform/{platform.system().lower()}.py"))

set_default(
    "MESSAGE_LEVEL", message_constants.DEBUG if DEBUG else message_constants.INFO
)

WSGI_APPLICATION = env(
    "WSGI_APPLICATION", default=get_setting("WSGI_APPLICATION", "slm.wsgi.application")
)

if SLM_ADMIN_MAP or "slm.map" in INSTALLED_APPS:
    include(resource("slm.map", "settings.py"))
if SLM_FILE_VIEWS or "slm.file_views" in INSTALLED_APPS:
    include(resource("slm.file_views", "settings.py"))
