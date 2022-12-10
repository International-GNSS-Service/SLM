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
        'Validate and update status of head state of all existing site logs.'
    )

    logger = logging.getLogger(__name__ + '.Command')

    SECTIONS = {
        'siteform_set',
        'siteidentification_set',
        'sitelocation_set',
        'sitereceiver_set',
        'siteantenna_set',
        'sitesurveyedlocalties_set',
        'sitefrequencystandard_set',
        'sitecollocation_set',
        'sitehumiditysensor_set',
        'sitepressuresensor_set',
        'sitetemperaturesensor_set',
        'sitewatervaporradiometer_set',
        'siteotherinstrumentation_set',
        'siteradiointerferences_set',
        'sitemultipathsources_set',
        'sitelocalepisodiceffects_set',
        'sitesignalobstructions_set',
        'siteoperationalcontact_set',
        'siteresponsibleagency_set',
        'sitemoreinformation_set'
    }

    def add_arguments(self, parser):

        parser.add_argument(
            '--bypass-blocks',
            dest='bypass',
            action='store_true',
            default=False,
            help=_(
                'Bypass any save blocking that validation triggers. Flags '
                'will be stored and the edits will be allowed.'
            )
        )

    def handle(self, *args, **options):

        if options['bypass']:
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
                            obj.clean()
                            obj.save()

                    site.update_status(save=True)
                    pbar.update(n=1)
