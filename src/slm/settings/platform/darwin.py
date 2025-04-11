# this is the default location Postgres.app with postgres will install the postgis libraries to
# if your system is different, or you use a different postgres package you will have to
# override these

GDAL_LIBRARY_PATH = (
    "/Applications/Postgres.app/Contents/Versions/latest/lib/libgdal.dylib"
)
GEOS_LIBRARY_PATH = (
    "/Applications/Postgres.app/Contents/Versions/latest/lib/libgeos_c.dylib"
)
