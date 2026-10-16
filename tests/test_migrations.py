"""
Migrations are remade at version waypoints (just remake-migrations). These
tests guard the invariants the remade migrations depend on.
"""

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from slm.migration_operations import SATELLITE_SYSTEMS


def test_replaced_migration_names_are_not_reused():
    """
    Databases migrated through a waypoint still have rows for every replaced
    migration. A new migration that reuses one of those names would be treated
    as already applied there, and Django drops replaced nodes from the graph.
    """
    loader = MigrationLoader(None, ignore_no_migrations=True, load=False)
    loader.load_disk()
    replaced = {
        key
        for migration in loader.disk_migrations.values()
        for key in (migration.replaces or [])
    }
    assert not replaced & set(loader.disk_migrations)


@pytest.mark.django_db
def test_install_operations_applied():
    """
    The test database is built from the migrations - make sure the operations
    model state cannot express were included.
    """
    from slm.models import SatelliteSystem

    assert set(SatelliteSystem.objects.values_list("name", flat=True)) == {
        name for name, _ in SATELLITE_SYSTEMS
    }
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'slm_archiveindex'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT conname FROM pg_constraint "
            "WHERE conname = 'index_valid_range_lower_not_null'"
        )
        constraints = cursor.fetchall()
    assert {"idx_archiveindex_lower_bound", "idx_archiveindex_upper_bound"} <= indexes
    assert constraints
