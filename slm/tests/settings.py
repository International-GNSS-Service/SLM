from pathlib import Path
import platform
from split_settings.tools import include

from slm.settings import resource

SITE_DIR = Path(__file__).resolve().parent / "tmp"

if platform.system().lower() == 'darwin':
    GDAL_LIBRARY_PATH = '/Applications/Postgres.app/Contents/Versions/latest/lib/libgdal.dylib'
    GEOS_LIBRARY_PATH = '/Applications/Postgres.app/Contents/Versions/latest/lib/libgeos_c.dylib'

include(resource("slm.settings", "root.py"))

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "slm_test",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}

SLM_PRELOAD_SCHEMAS = False

COMPRESS_ENABLED = False
