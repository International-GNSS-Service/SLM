from split_settings.tools import include
from pathlib import Path
import getpass

WSGI_APPLICATION = "sites.{{ site }}.production.wsgi.application"

DEBUG = False
SITE_DIR = Path("{{ production_dir }}")
BASE_DIR = SITE_DIR

ALLOWED_HOSTS = [
    '{{ netloc }}',
    # in some production configurations you may need to add your server's ip address
    # to this list
]
SLM_SITE_NAME = '{{ netloc }}'


MEDIA_ROOT = SITE_DIR / 'media'
STATIC_ROOT = SITE_DIR / 'static'


# This section deals with database connection. Alterations may need to be made for
# deployment. We recommend running a database locally and using postgres user
# authentication and disallowing any non-local connections. This means your database
# is as secure as the system user running your SLM deployment.
# 
# You may of course, use any number of database settings or have multiple databases:
# https://docs.djangoproject.com/en/stable/ref/databases/
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '{{ site }}',
        'USER': getpass.getuser(),  # if postgres is configured for user authentication
        'ATOMIC_REQUESTS': True
    },
}

# The SLM uses geodjango. Unless gdal and geos are in standard locations on your production
# server you will have to set their paths explicitly here:
# https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/geolibs/
# TODO
# GDAL_LIBRARY_PATH = "/path/to/libgdal.so"
# GEOS_LIBRARY_PATH = '/path/to/libgeos_c.so.1'

# Make sure debug toolbar is not run in production - it can expose secrets!
DJANGO_DEBUG_TOOLBAR = False

include('../base.py')

# ADMINS will receive email notifications when exceptions are encountered or 500 errors
# returned to user requests
ADMINS = [
    #("Your Name", "Email Address")
]

# Change this setting if you would like the links serialized into site logs or geodesyml
# files to use a different domain than the one of this deployment.
# For example, IGS's SLM is running on https://slm.igs.org but our public facing downloads
# are from https://network.igs.org
# SLM_FILE_DOMAIN = 'https://{{ netloc }}'
