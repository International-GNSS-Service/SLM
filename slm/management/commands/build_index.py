"""
Update the data availability information for each station.
"""
import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import gettext as _
from slm.models import Site, ArchiveIndex
from slm.defines import SiteLogStatus
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Update the site index from the current data or rebuild from ' \
           'archives. Note - this will generate new serialized files for all' \
           'published data that is not up to date in the archive.'

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
                    'be undone if you do not have an external archive! '
                    'Proceed? (Y/N): '
                ))):
                    ArchiveIndex.objects.all().delete()
                else:
                    return

            if options['archive']:
                # todo
                raise NotImplementedError(
                    'Rebuild from archive not implemented yet!'
                )

            sites = Site.objects.public().filter(
                status=SiteLogStatus.PUBLISHED
            )
            # build from current data
            with tqdm(
                total=sites.count(),
                desc='Indexing',
                unit='sites',
                postfix={'site': ''}
            ) as p_bar:
                for site in sites:
                    p_bar.set_postfix({'site': site.name})
                    ArchiveIndex.objects.add_index(site=site)
                    p_bar.update(n=1)
