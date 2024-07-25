from pathlib import Path
import platform
from split_settings.tools import include
import os

from slm.settings import resource

SITE_DIR = Path(__file__).resolve().parent / "tmp"

if platform.system().lower() == 'darwin':
    GDAL_LIBRARY_PATH = '/Applications/Postgres.app/Contents/Versions/latest/lib/libgdal.dylib'
    GEOS_LIBRARY_PATH = '/Applications/Postgres.app/Contents/Versions/latest/lib/libgeos_c.dylib'

include(resource("slm.settings", "root.py"))

INSTALLED_APPS = [
    'django_extensions',
    *INSTALLED_APPS
]

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGRES_DB", "slm_test"),
        "USER": os.environ.get('POSTGRES_USER', ''),
        "PASSWORD": os.environ.get('POSTGRES_PASSWORD', ''),
        "HOST": os.environ.get("POSTGRES_HOST", ""),
        "PORT": os.environ.get("POSTGRES_PORT", ""),
    }
}

SLM_PRELOAD_SCHEMAS = False

COMPRESS_ENABLED = False
