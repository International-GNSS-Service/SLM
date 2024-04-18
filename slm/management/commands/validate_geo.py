"""
Update the data availability information for each station.
"""

import logging

from django.core.management import BaseCommand
from django.utils.translation import gettext as _
from lxml import etree

from slm.defines import GeodesyMLVersion


class Command(BaseCommand):
    help = _("Validate the given xml document against the GeodesyML schema.")

    logger = logging.getLogger(__name__ + ".Command")

    def add_arguments(self, parser):
        parser.add_argument(
            "GeodesyML",
            metavar="GML",
            nargs=1,
            help=_("Path to the GML file to validate."),
        )

        parser.add_argument(
            "--geo",
            type=str,
            dest="version",
            default=None,
            help=_(
                f"The Geodesy ML version "
                f'({", ".join([str(v.version) for v in GeodesyMLVersion])}).'
            ),
        )

    def handle(self, *args, **options):
        doc = etree.parse(options["GeodesyML"][0])
        root = doc.getroot()

        geo = (
            GeodesyMLVersion(options["version"])
            if options.get("version", None)
            else GeodesyMLVersion(
                root.nsmap.get(root.prefix, GeodesyMLVersion.latest())
            )
        )

        print(f"Validating against: {str(geo)}")

        result = geo.schema.validate(doc)

        if not result:
            for error in geo.schema.error_log:
                print(f"[{error.line}] {error.message}")
        else:
            print(f'{options["GeodesyML"][0]} is valid!')
