"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.utils.translation import gettext as _
from slm.defines import GeodesyMLVersion
from lxml import etree


class Command(BaseCommand):

    help = _(
        'Generate a GML document from the edit stack for a given site and '
        'valid for the given the GeodesyML schema.'
    )

    logger = logging.getLogger(__name__ + '.Command')

    def add_arguments(self, parser):

        parser.add_argument(
            'site',
            metavar='S',
            nargs=1,
            help=_('The name of the site.')
        )

        parser.add_argument(
            '--geo',
            type=GeodesyMLVersion,
            dest='version',
            default=GeodesyMLVersion.latest(),
            help=_(
                f'The Geodesy ML version '
                f'({", ".join([str(v.version) for v in GeodesyMLVersion])}).'
            )
        )

    def handle(self, *args, **options):
        pass
