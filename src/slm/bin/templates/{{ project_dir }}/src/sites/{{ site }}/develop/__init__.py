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

BASE_DIR = Path(__file__).resolve().parent

DEBUG = True
SLM_DEBUG_TOOLBAR = True

WSGI_APPLICATION = "sites.{{ site }}.develop.wsgi.application"

set_default("SILENCED_SYSTEM_CHECKS", []).extend([
    "security.W004",
    "security.W008",
    "security.W018"
])

include('../base.py')

# Special configuration parameters for your local development instance should be
# placed here:
include(optional('local.py'))

INSTALLED_APPS.insert(1, 'django_extensions')

SECURE_SSL_REDIRECT = False
