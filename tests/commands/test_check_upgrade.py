"""
Version waypoint checks - see doc/source/upgrading.rst

A waypoint is a release whose database state the following release's remade
migrations start from. Databases must be migrated by the waypoint release
before moving past it, and cannot be migrated back across it.
"""

import pytest
from django.core.management import CommandError, call_command
from django.db.migrations.recorder import MigrationRecorder
from packaging.version import parse

from slm.management.commands.check_upgrade import Command as CheckUpgrade
from slm.models import SLMVersion

WAYPOINTS = [parse("0.5.0b0"), parse("0.8.0")]


@pytest.fixture
def versions(db, monkeypatch):
    monkeypatch.setattr(CheckUpgrade, "VERSION_WAYPOINTS", WAYPOINTS)

    def set_versions(db_version, installed):
        SLMVersion.update(db_version)
        monkeypatch.setattr(CheckUpgrade, "slm_version", parse(installed))

    return set_versions


@pytest.mark.parametrize(
    "db_version,installed",
    [
        ("0.4.1b0", "0.4.1b0"),  # no change
        ("0.4.0b0", "0.4.1b0"),  # upgrade before any waypoint
        ("0.4.1b0", "0.5.0b0"),  # upgrade to the waypoint
        ("0.5.0b0", "0.6.0b0"),  # upgrade from the waypoint
        ("0.5.0b0", "0.8.0"),  # upgrade from one waypoint to the next
        ("0.6.0b0", "0.7.0"),  # upgrade between waypoints
        ("0.7.0", "0.6.0b0"),  # downgrade between waypoints
        ("0.5.0b0", "0.4.1b0"),  # downgrade from the waypoint
    ],
)
def test_safe(versions, db_version, installed):
    versions(db_version, installed)
    CheckUpgrade().is_safe()


@pytest.mark.parametrize(
    "db_version,installed,waypoint",
    [
        ("0.4.1b0", "0.6.0b0", "0.5.0b0"),  # upgrade skips the waypoint
        ("0.4.1b0", "0.9.0", "0.5.0b0"),  # upgrade skips both waypoints
        ("0.6.0b0", "0.9.0", "0.8.0"),  # upgrade skips the second waypoint
        ("0.6.0b0", "0.5.0b0", "0.5.0b0"),  # downgrade to the waypoint
        ("0.6.0b0", "0.4.1b0", "0.5.0b0"),  # downgrade past the waypoint
    ],
)
def test_unsafe(versions, db_version, installed, waypoint):
    versions(db_version, installed)
    with pytest.raises(CommandError, match=f"waypoint: {waypoint}"):
        CheckUpgrade().is_safe()


def test_fresh_database(versions):
    """
    A database SLM has never been migrated on can be migrated by any version.
    """
    versions("0.4.1b0", "0.9.0")
    SLMVersion.objects.all().delete()
    MigrationRecorder.Migration.objects.filter(app="slm").delete()
    assert CheckUpgrade().db_version is None
    CheckUpgrade().is_safe()


def test_unversioned_database(versions):
    """
    Databases migrated before SLMVersion existed are treated as 0.1.4b.
    """
    versions("0.4.1b0", "0.4.1b0")
    SLMVersion.objects.all().delete()
    assert CheckUpgrade().db_version == parse("0.1.4b")


def test_migrate_refuses_unsafe_upgrade(versions):
    versions("0.4.1b0", "0.6.0b0")
    with pytest.raises(CommandError, match="waypoint: 0.5.0b0"):
        call_command("migrate", verbosity=0)
    # the recorded database version must not change
    assert SLMVersion.load().version == parse("0.4.1b0")
