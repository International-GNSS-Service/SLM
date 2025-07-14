# this is the default location Postgres.app with postgres will install the postgis libraries to
# if your system is different, or you use a different postgres package you will have to
# override these
from slm.settings import env as settings_environment
from slm.settings import get_setting

env = settings_environment()

GDAL_LIBRARY_PATH = env(
    "GDAL_LIBRARY_PATH",
    default=get_setting(
        "GDAL_LIBRARY_PATH",
        "/Applications/Postgres.app/Contents/Versions/latest/lib/libgdal.dylib",
    ),
)
GEOS_LIBRARY_PATH = env(
    "GEOS_LIBRARY_PATH",
    default=get_setting(
        "GEOS_LIBRARY_PATH",
        "/Applications/Postgres.app/Contents/Versions/latest/lib/libgeos_c.dylib",
    ),
)
