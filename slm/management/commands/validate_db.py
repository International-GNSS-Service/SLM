"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import gettext as _
from slm.models.sitelog import *
from tqdm import tqdm


class Command(BaseCommand):

    help = _(
        'Validate and update status of head state of all existing site logs. '
        'This might be necessary to run if the validation configuration is '
        'updated.'
    )

    logger = logging.getLogger(__name__ + '.Command')

    SECTIONS = {
        *Site.section_accessors(),
        *Site.subsection_accessors(),
    }

    def add_arguments(self, parser):

        parser.add_argument(
            '--clear',
            dest='clear',
            action='store_true',
            default=False,
            help=_('Clear existing validation flags.')
        )

    def handle(self, *args, **options):

        from slm.validators import set_bypass
        set_bypass(True)

        with transaction.atomic():

            with tqdm(
                total=Site.objects.count(),
                desc='Validating',
                unit='sites',
                postfix={'site': ''}
            ) as pbar:
                for site in Site.objects.all():
                    pbar.set_postfix({'site': site.name})
                    for section in self.SECTIONS:
                        head = getattr(site, section).head()
                        if not hasattr(head, '__iter__'):
                            head = [head]
                        for obj in head:
                            if options['clear']:
                                obj._flags = {}
                            obj.clean()
                            obj.save()

                    site.update_status(save=True)
                    pbar.update(n=1)
