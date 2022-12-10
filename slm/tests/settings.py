from pathlib import Path

from slm.settings import resource
from split_settings.tools import include

SITE_DIR = Path(__file__).resolve().parent / 'tmp'

include(resource('slm.settings', 'root.py'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
