"""
Database operations that model state cannot express and makemigrations will
therefore never regenerate.

``just remake-migrations`` appends :func:`install_operations` to the first slm
migration each time the migrations are remade at a version waypoint. That
migration replaces all prior migrations, so these operations only run on fresh
databases - databases migrated through the waypoint already have them.

Changes here only affect fresh installs. Changes that must also reach existing
databases need their own migration.
"""

from django.db import migrations

SATELLITE_SYSTEMS = [
    ("GPS", 0),
    ("GLO", 1),
    ("GAL", 2),
    ("BDS", 3),
    ("QZSS", 4),
    ("IRNSS", 5),
    ("SBAS", 6),
    ("WAAS", 7),
]


def load_satellite_systems(apps, schema_editor):
    SatelliteSystem = apps.get_model("slm", "SatelliteSystem")
    for name, order in SATELLITE_SYSTEMS:
        SatelliteSystem.objects.get_or_create(name=name, defaults={"order": order})


def unload_satellite_systems(apps, schema_editor):
    SatelliteSystem = apps.get_model("slm", "SatelliteSystem")
    SatelliteSystem.objects.filter(name__in=[n for n, _ in SATELLITE_SYSTEMS]).delete()


def install_operations():
    return [
        migrations.RunPython(load_satellite_systems, unload_satellite_systems),
        # expression indexes on the archive index validity range bounds
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_archiveindex_lower_bound
                ON slm_archiveindex (lower(valid_range));
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_archiveindex_lower_bound;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_archiveindex_upper_bound
                ON slm_archiveindex (upper(valid_range));
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_archiveindex_upper_bound;",
        ),
        migrations.RunSQL(
            sql="""
                ALTER TABLE slm_archiveindex
                ADD CONSTRAINT index_valid_range_lower_not_null
                CHECK (lower(valid_range) IS NOT NULL);
            """,
            reverse_sql="""
                ALTER TABLE slm_archiveindex
                DROP CONSTRAINT IF EXISTS index_valid_range_lower_not_null;
            """,
        ),
    ]
