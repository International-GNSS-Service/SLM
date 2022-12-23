"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand, CommandError
from django.utils.translation import gettext as _
from slm.models import Site
from django.contrib.sites.models import Site
from django.conf import settings


class Command(BaseCommand):

    help = _(
        'Set the Django Site database object to reflect SLM_SITE_NAME and '
        'SLM_ORG_NAME in settings.'
    )

    logger = logging.getLogger(__name__ + '.Command')

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        domain = getattr(settings, 'SLM_SITE_NAME', None)
        org = getattr(settings, 'SLM_ORG_NAME', None)
        if domain and org:
            site = Site.objects.get_current()
            site.domain = domain
            site.name = org
            site.save()
        else:
            raise CommandError(
                f'To set the default Site object, both SLM_SITE_NAME and '
                f'SLM_ORG_NAME must be defined in settings.'
            )
