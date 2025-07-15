from split_settings.tools import include
from pathlib import Path

WSGI_APPLICATION = "sites.{{ site }}.production.wsgi.application"

DEBUG = False
BASE_DIR = Path("{{ production_dir }}")

ALLOWED_HOSTS = [
    '{{ netloc }}',
    # in some production configurations you may need to add your server's ip address
    # to this list
]
SLM_SITE_NAME = '{{ netloc }}'

# The SLM uses geodjango. Unless gdal and geos are in standard locations on your production
# server you will have to set their paths explicitly here:
# https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/geolibs/
# TODO
# GDAL_LIBRARY_PATH = "/path/to/libgdal.so"
# GEOS_LIBRARY_PATH = '/path/to/libgeos_c.so.1'

# Make sure debug toolbar is not run in production - it can expose secrets!
SLM_DEBUG_TOOLBAR = False

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

include('../base.py')


