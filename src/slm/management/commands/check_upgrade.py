"""
Occasionally it is helpful to delete all the migration files and start anew with one
simple initial migration. Changes accumulate over time, or old migration files may
cause errors on new software stacks. This command facilitates a transition back to
one initial migration file on a version upgrade. One side effect of this is that you
may need to migrate through multiple versions instead of being able to make one big
jump. This command will check for these cases and fail if the migration from the
current software version is unsafe on the current database version.
"""

import bisect
import typing as t

import typer
from django.core.management import CommandError
from django.db import ProgrammingError, connection
from django.db.migrations.loader import MigrationLoader
from django.utils.translation import gettext as _
from django_typer.management import TyperCommand, command
from packaging.version import InvalidVersion, Version, parse
from typing_extensions import Annotated

from slm import __version__ as slm_version
from slm.models import SLMVersion


def parse_version(version: str) -> Version:
    try:
        return parse(version)
    except InvalidVersion as verr:
        raise typer.BadParameter(
            f"{version} is not a valid Python package version string."
        ) from verr


def get_ordered_migration_paths(app_label):
    loader = MigrationLoader(connection)
    graph = loader.graph

    app_migrations = [key for key in graph.nodes.keys() if key[0] == app_label]

    if not app_migrations:
        raise ValueError(f"No migrations found for app '{app_label}'")

    latest_keys = graph.leaf_nodes(app_label)

    # Get the full dependency plan (in order)
    plan = []
    for latest in latest_keys:
        plan.extend(graph.forwards_plan(latest))

    # De-duplicate and filter only this app's migrations
    seen = set()
    ordered_keys = [
        m for m in plan if m[0] == app_label and not (m in seen or seen.add(m))
    ]

    return [loader.get_migration(app, name) for app, name in ordered_keys]


class Command(TyperCommand):
    help = _(
        "Make sure the attempted upgrade is safe. And if it is, make any migration table "
        "edits that are necessary."
    )

    # when upgrading the SLM it is required that an upgrade run through
    # these specific versions. These versions are points at which the migration
    # files were remade - meaning the database state may not be migrated correctly
    # if it was not first updated to be state consistent with these specific versions.
    VERSION_WAYPOINTS = []  # list(sorted([parse("0.2.0b0")]))

    requires_migrations_checks = False
    requires_system_checks = []

    slm_version = parse_version(slm_version)

    @property
    def db_version(self) -> Version:
        try:
            return SLMVersion.load().version or parse("0.1.4b")
        except ProgrammingError:
            return parse("0.1.4b")

    def closest_waypoint_gte(self, version: Version) -> t.Optional[Version]:
        idx = bisect.bisect_left(self.VERSION_WAYPOINTS, version)
        if idx < len(self.VERSION_WAYPOINTS):
            return self.VERSION_WAYPOINTS[idx]
        return None

    def closest_waypoint_lte(self, version: Version) -> t.Optional[Version]:
        idx = bisect.bisect_right(self.VERSION_WAYPOINTS, version)
        if idx > 0:
            return self.VERSION_WAYPOINTS[idx - 1]
        return None

    @command(
        help="Check that it is safe to run migrations from the installed version of igs-slm."
    )
    def is_safe(self):
        if self.db_version > self.slm_version:
            # downgrades are possible with reversible migrations - we only
            # balk if the downgrade would travel through a migration waypoint
            nearest_waypoint = self.closest_waypoint_lte(self.db_version)
            if nearest_waypoint and nearest_waypoint > self.slm_version:
                raise CommandError(
                    f"Unable to downgrade from {self.db_version} to {self.slm_version}. "
                    f"Traverses version waypoint: {nearest_waypoint}. "
                    f"It is recommended that you restore from a database backup."
                )
        elif self.db_version < self.slm_version:
            # Upgrades must pass through all waypoints between the database code version and
            # the installed version of igs-slm
            nearest_waypoint = self.closest_waypoint_gte(self.db_version)
            if nearest_waypoint and nearest_waypoint < self.slm_version:
                raise CommandError(
                    f"Unable to upgrade from {self.db_version} to {self.slm_version}. "
                    f"Traverses version waypoint: {nearest_waypoint}. "
                    f"You must first install and upgrade SLM at the waypoint: "
                    f"pip install igs-slm=={nearest_waypoint}."
                )

    @command(
        help="Force the database igs-slm version to the installed igs-slm version or the given value."
    )
    def set_db_version(
        self,
        version: Annotated[
            t.Optional[Version],
            typer.Option(
                help="The version string to set in the database if different than installed.",
                parser=parse_version,
            ),
        ] = None,
    ):
        version = version or self.slm_version
        if version != self.db_version:
            confirm = typer.confirm(
                _(
                    "You are about to force the database to record the version of the igs-slm "
                    f"software it is structurally synchronized to "
                    f"({self.db_version} -> {version}). Are you sure you want to do this?"
                )
            )
            if not confirm:
                self.secho(_("Aborted."), fg="red")
                raise typer.Exit(code=1)
            try:
                SLMVersion.update(version=version)
            except ProgrammingError:
                # this could happen if we are backwards migrating and the table no longer
                # exists, but we're called via a migrate signal
                pass
