"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import gettext as _
from slm.models import Site
from slm.defines import GeodesyMLVersion, SiteLogFormat
from slm.api.serializers import SiteLogSerializer
from tqdm import tqdm
from lxml import etree


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

        parser.add_argument(
            '--schema',
            dest='schema',
            action='store_true',
            default=False,
            help=_(
                'Also perform validation of generated GeodesyML files '
                'against the latest schema.'
            )
        )

    def handle(self, *args, **options):

        from slm.validators import set_bypass
        set_bypass(True)
        invalid = 0
        valid = 0
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

                    if options['schema']:
                        geo_version = GeodesyMLVersion.latest()

                        try:
                            result = geo_version.schema.validate(
                                etree.fromstring(
                                    SiteLogSerializer(instance=site).format(
                                        SiteLogFormat.GEODESY_ML,
                                        version=geo_version
                                    )
                                )
                            )
                            if not result:
                                invalid += 1
                                print(f'[{site.name}] did not validate.')

                                for error in geo_version.schema.error_log:
                                    print(f'[{error.line}] {error.message}')
                            else:
                                valid += 1
                        except Exception as exc:
                            print(
                                f'[{site.name}] failed to generate xml: {exc}'
                            )
                            invalid += 1

                    site.update_status(save=True)
                    pbar.update(n=1)

        if options['schema']:
            print(
                f'{valid} sites had valid GeodesyML documents while {invalid} '
                f'sites did not.'
            )
