"""
This is the local Django configuration for the development configuration of your SLM
project.
"""

from split_settings.tools import (
    include,
    optional
)
from slm.settings import set_default
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
BASE_DIR = SITE_DIR

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

DEBUG = True
DJANGO_DEBUG_TOOLBAR = True

include('../base.py')

set_default("SILENCED_SYSTEM_CHECKS", []).extend([
    "security.W004",
    "security.W008",
    "security.W018"
])

# Special configuration parameters for your local development instance should be
# placed here:
include(optional('local.py'))

set_default(
    'DATABASES',
    {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': '{{ site }}',
            'USER': 'postgres',
            'PASSWORD': '',
            'ATOMIC_REQUESTS': True,
        }
    }
)

WSGI_APPLICATION = "sites.{{ site }}.develop.wsgi.application"

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

INSTALLED_APPS.insert(1, 'django_extensions')

SECURE_SSL_REDIRECT = False
