"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _
from slm.models import Site, GeodesyMLInvalid
from slm.defines import SiteLogStatus
from django.db.models import Sum
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
        critical = 0
        old_flag_count = Site.objects.aggregate(
            Sum('num_flags')
        )['num_flags__sum']
        with transaction.atomic():
            
            sites = Site.objects.filter(status__in=[
                SiteLogStatus.PUBLISHED,
                SiteLogStatus.UPDATED
            ])
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
                            if head:
                                head = [head]
                            else:
                                head = []
                        for obj in head:
                            if options['clear']:
                                obj._flags = {}
                            try:
                                obj.clean()
                                obj.save()
                            except ValidationError as verr:
                                self.stderr.write(
                                    self.style.ERROR(
                                        _(
                                            'Section {} of site {} has '
                                            'critical error(s): {}'
                                        ).format(
                                            obj.__class__.__name__.lstrip(
                                                'Site'
                                            ),
                                            site.name,
                                            str(verr)
                                        )
                                    )
                                )
                                critical += 1
                                # this type of error would normally block the
                                # section from being saved - but we let this
                                # go through here and record the error as a
                                # normal flag
                                for field, errors in verr.error_dict.items():
                                    obj._flags[field] = '\n'.join(
                                        err.message for err in errors
                                    )

                    if options['schema']:
                        alert = GeodesyMLInvalid.objects.check_site(site=site)
                        if alert:
                            invalid += 1
                        else:
                            valid += 1

                    #site.update_status(save=True)
                    p_bar.update(n=1)

            Site.objects.synchronize_denormalized_state(skip_form_updates=True)

        if options['schema']:
            if valid:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{valid} sites had valid GeodesyML documents.'
                    )
                )
            if invalid:
                self.stdout.write(
                    self.style.ERROR(
                        f'{invalid} sites do not have valid GeodesyML '
                        f'documents.'
                    )
                )

        new_flags = Site.objects.aggregate(
            Sum('num_flags')
        )['num_flags__sum']

        delta = new_flags - old_flag_count

        if delta >= 0:
            change = 'added'
        else:
            change = 'removed'

        self.stdout.write(
            self.style.NOTICE(
                f'{abs(delta)} flags were {change}.'
            )
        )

        self.stdout.write(self.style.NOTICE(
            f'There are a total of validation {new_flags} across '
            f'{sites.count()} sites. {critical} are critical.'
        ))
