"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import gettext as _
from slm.models import Site, SiteIndex
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Update the site index from the current data or rebuild from ' \
           'archives.'

    logger = logging.getLogger(__name__ + '.Command')

    def add_arguments(self, parser):

        parser.add_argument(
            '--rebuild',
            dest='rebuild',
            action='store_true',
            default=False,
            help=_(
                'Clear the existing index first. WARNING: cannot be undone.'
            )
        )

        parser.add_argument(
            '-a',
            '--archive',
            dest='archive',
            type=str,
            default=False,
            help=_('Build index from the archive directory.')
        )

    def handle(self, *args, **options):

        with transaction.atomic():

            def yes(ipt):
                return ipt.lower() in {'y', 'yes', 'true', 'continue'}

            if options['rebuild']:
                if yes(input(_(
                    'WARNING: this will delete the current index. This cannot '
                    'be undone if you do not have an external archive! Proceed? '
                    '(Y/N): '
                ))):
                    SiteIndex.objects.all().delete()
                else:
                    return

            if options['archive']:
                # todo
                raise NotImplementedError(
                    'Rebuild from archive not implemented yet!'
                )

            # build from current data
            with tqdm(
                total=Site.objects.public().count(),
                desc='Indexing',
                unit='sites',
                postfix={'site': ''}
            ) as pbar:
                for site in Site.objects.public():
                    pbar.set_postfix({'site': site.name})
                    SiteIndex.objects.add_index(site=site)
                    pbar.update(n=1)

