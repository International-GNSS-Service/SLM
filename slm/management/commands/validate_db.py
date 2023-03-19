"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import gettext as _
from slm.models import Site, GeodesyMLInvalid
from tqdm import tqdm


class Command(BaseCommand):

    help = _(
        'Validate and update status of head state of all existing site logs. '
        'This might be necessary to run if the validation configuration is '
        'updated.'
    )

    logger = logging.getLogger(__name__ + '.Command')

    def add_arguments(self, parser):

        parser.add_argument(
            'sites',
            metavar='S',
            nargs='*',
            help=_('The name of the site(s). Default - all sites.')
        )

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
        
        parser.add_argument(
            '--all',
            dest='all',
            action='store_true',
            default=False,
            help=_(
                'Validate all sites, not just the currently public sites.'
            )
        )

    def handle(self, *args, **options):

        from slm.validators import set_bypass
        set_bypass(True)
        invalid = 0
        valid = 0
        with transaction.atomic():
            
            sites = Site.objects.public()
            if options['all']:
                sites = Site.objects.all()

            if options['sites']:
                sites = Site.objects.filter(
                    name__in=[site.upper() for site in options['sites']]
                )

            with tqdm(
                total=sites.count(),
                desc='Validating',
                unit='sites',
                postfix={'site': ''}
            ) as p_bar:
                for site in sites:
                    p_bar.set_postfix({'site': site.name})
                    for section in Site.sections():
                        head = getattr(site, section.accessor).head()
                        if not hasattr(head, '__iter__'):
                            head = [head]
                        for obj in head:
                            if options['clear']:
                                obj._flags = {}
                            obj.clean()
                            obj.save()

                    if options['schema']:
                        alert = GeodesyMLInvalid.objects.check_site(site=site)
                        if alert:
                            invalid += 1
                        else:
                            valid += 1

                    #site.update_status(save=True)
                    p_bar.update(n=1)

            Site.objects.synchronize_denormalized_metrics()

        if options['schema']:
            print(
                f'{valid} sites had valid GeodesyML documents while {invalid} '
                f'sites did not.'
            )
