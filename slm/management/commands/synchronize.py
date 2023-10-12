"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext as _
from slm.models import Site


class Command(BaseCommand):
    help = _(
        'Synchronize all denormalized data - that is data that is cached for '
        'performance reasons that may become out of sync if updates are '
        'performed outside of normal request/response cycles.'
    )

    logger = logging.getLogger(__name__ + '.Command')

    def add_arguments(self, parser):
        parser.add_argument(
            'stations',
            metavar='S',
            nargs='*',
            type=str,
            help=_(
                'The station(s) to update, if unspecified, update data '
                'availability information for all of them.'
            )
        )

    def handle(self, *args, **options):

        with transaction.atomic():
            qry = Q()
            if options['stations']:
                for stn in options['stations']:
                    qry |= Q(name__istartswith=stn)
            Site.objects.filter(qry).synchronize_denormalized_state()
