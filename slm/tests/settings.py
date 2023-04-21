from pathlib import Path

from slm.settings import resource
from split_settings.tools import include

SITE_DIR = Path(__file__).resolve().parent / 'tmp'

GDAL_LIBRARY_PATH = '/Applications/Postgres.app/Contents/Versions/12/lib/libgdal.26.dylib'
GEOS_LIBRARY_PATH = '/Applications/Postgres.app/Contents/Versions/12/lib/libgeos_c.dylib'

include(resource('slm.settings', 'root.py'))

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'test.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

SLM_PRELOAD_SCHEMAS = False

