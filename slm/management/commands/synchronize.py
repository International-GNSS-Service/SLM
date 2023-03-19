"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import gettext as _
from slm.models import Site


class Command(BaseCommand):
    help = _(
        'Synchronize all denormalized data - that is data that is cached for '
        'performance reasons that may become out of sync if updates are '
        'performed outside of normal request/response cycles.'
    )

    logger = logging.getLogger(__name__ + '.Command')

    def handle(self, *args, **options):

        with transaction.atomic():
            Site.objects.synchronize_denormalized_metrics()
