# this is the default location Postgres.app with postgres will install the postgis libraries to
# if your system is different, or you use a different postgres package you will have to
# override these
from pathlib import Path

from slm.settings import get_setting

if not get_setting("GDAL_LIBRARY_PATH"):
    gdal_postgres_app_path = Path(
        "/Applications/Postgres.app/Contents/Versions/latest/lib/libgdal.dylib"
    )
    if gdal_postgres_app_path.is_file():
        GDAL_LIBRARY_PATH = str(gdal_postgres_app_path)

if not get_setting("GEOS_LIBRARY_PATH"):
    geos_postgres_app_path = Path(
        "/Applications/Postgres.app/Contents/Versions/latest/lib/libgeos_c.dylib"
    )
    if geos_postgres_app_path.is_file():
        GEOS_LIBRARY_PATH = str(geos_postgres_app_path)
