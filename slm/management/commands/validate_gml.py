"""
Update the data availability information for each station.
"""

import typing as t
from pathlib import Path

from django.core.management import CommandError
from django.utils.translation import gettext as _
from django_typer.management import TyperCommand
from lxml import etree
from typer import Argument, Option
from typing_extensions import Annotated

from slm.defines import GeodesyMLVersion
from slm.management.commands import EnumParser


class Command(TyperCommand):
    help = _("Validate the given xml document against the GeodesyML schema.")

    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        #    "version",
        "pythonpath",
        "settings",
        "skip-checks",
    }
    requires_migrations_checks = False
    requires_system_checks = []

    def handle(
        self,
        file: Annotated[Path, Argument(help=_("Path to the GML file to validate."))],
        version: Annotated[
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
        if not file.exists():
            raise CommandError(_("{file} does not exist!").format(file=file))
        doc = etree.parse(file)
        root = doc.getroot()

        if not version:
            version = GeodesyMLVersion(
                root.nsmap.get(root.prefix, GeodesyMLVersion.latest())
            )

        self.stdout.write(_("Validating against: {version}").format(version=version))

        result = version.schema.validate(doc)

        if not result:
            for error in version.schema.error_log:
                self.stdout.write(
                    self.style.ERROR(
                        _("[{line}] {message}").format(
                            line=error.line, message=error.message
                        )
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(_("{file} is valid!").format(file=file))
            )
