"""
Generate a serialized site log of the given format for a station's published or
unpublished head state. Optionally the file will be pulled from the index of archived
site log files.

It is usually more convenient to go through the web interface if you just want to view
a sitelog, but this command can be useful for entering into the debugger to troubleshoot
parts of this pipeline.
"""

import typing as t
from datetime import datetime
from pathlib import Path

from django.core.management import CommandError
from django.db.models import Q
from django.utils.translation import gettext as _
from django_typer.management import (
    TyperCommand,
    command,
    initialize,
    model_parser_completer,
)
from typer import Argument, Option
from typing_extensions import Annotated

from slm.api.serializers import SiteLogSerializer
from slm.defines import GeodesyMLVersion, SiteLogFormat
from slm.management.commands import EnumParser
from slm.models import ArchiveIndex, Site


class Command(TyperCommand):
    help = _(
        "Generate a site log in the specified format for the specified site "
        "and print it to stdout. Optionally pull the log from the archive or "
        "regenerate it based on given parameters."
    )

    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        "version",
        "pythonpath",
        "settings",
        "skip-checks",
    }
    requires_migrations_checks = False
    requires_system_checks = []

    site: Site
    head: bool
    archive: bool

    @initialize()
    def set_site(
        self,
        site: Annotated[
            Site,
            Argument(
                **model_parser_completer(
                    Site, lookup_field="name", case_insensitive=True
                ),
                help=_("The name of the site."),
            ),
        ],
        head: Annotated[
            bool,
            Option(
                "--head", help=_("Generate the log from the head edits (unpublished).")
            ),
        ] = False,
        archive: Annotated[  # todo, should be mutually exclusive with head
            t.Optional[datetime],
            Option(help=_("Pull from archive rather than generating.")),
        ] = None,
    ):
        self.site = site
        if head and archive:
            raise CommandError("Cannot specify both --head and --archive.")
        self.head = head
        self.archive = archive

    @command()
    def legacy(self):
        if self.archive:
            index = ArchiveIndex.objects.filter(site=self.site).first()
            log_file = index.files.filter(log_format=SiteLogFormat.LEGACY).first()
            if not log_file:
                raise CommandError(
                    _("Latest index of {site} does not have a legacy log file.").format(
                        site=self.site.name
                    )
                )

            self.stdout.write(Path(log_file.file.path).read_text())
        else:
            self.stdout.write(
                SiteLogSerializer(
                    instance=self.site, published=None if self.head else True
                ).format(SiteLogFormat.LEGACY)
            )

    @command()
    def xml(
        self,
        gml_version: Annotated[
            t.Optional[GeodesyMLVersion],
            Option(
                "--version",
                metavar="VERSION",
                parser=EnumParser(GeodesyMLVersion, "version"),
                help=_("The Geodesy ML version. ({versions})").format(
                    versions=", ".join([str(gml.version) for gml in GeodesyMLVersion])
                ),
            ),
        ] = None,
    ):
        if self.archive:
            index = ArchiveIndex.objects.filter(site=self.site).first()
            qry = Q(log_format=SiteLogFormat.GEODESY_ML)
            qry &= Q(index__valid_range__contains=self.archive)
            if gml_version:
                qry &= Q(gml_version=gml_version)
            log_file = index.files.filter(qry).first()
            if not log_file:
                raise CommandError(
                    _(
                        "Archive of {site} @ {archive} does not have a {version} log file."
                    ).format(
                        site=self.site.name,
                        archive=self.archive,
                        version=str(gml_version) or "GeodesyML",
                    )
                )

            self.stdout.write(Path(log_file.file.path).read_text())
        else:
            self.stdout.write(
                SiteLogSerializer(
                    instance=self.site, published=None if self.head else True
                ).format(SiteLogFormat.GEODESY_ML, version=gml_version)
            )
