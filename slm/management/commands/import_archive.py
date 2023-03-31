"""
Import an archive file of old site logs - creating indexes and
ArchivedLogFiles.
"""
from django.core.management import BaseCommand, CommandError
from slm.defines import (
    SLMFileType,
)
import logging
from django.utils.translation import gettext as _
import tarfile
from tqdm import tqdm
import os
import re
from slm.models import (
    Site,
    ArchivedSiteLog,
    ArchiveIndex,
    Receiver,
    Antenna,
    Radome
)
from slm.defines import SiteLogFormat
from django.core.files.base import ContentFile
from django.db import transaction
from dateutil import parser
from slm.parsing.legacy import (
    SiteLogParser,
    SiteLogBinder
)
from datetime import datetime, date
from django.utils.timezone import utc, make_aware
from slm.utils import dddmmssss_to_decimal


# this matches fourYYMM.log and four_YYYYMMDD.log styles
FILE_NAME_REGEX = re.compile(r'^([a-zA-Z\d]{4,9})\D*(\d{4,8}).*log$')


class Command(BaseCommand):
    help = 'Import an archive file of old site logs - creating indexes and ' \
           'ArchivedLogFiles.'

    logger = logging.getLogger(__name__ + '.Command')

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            metavar='F',
            nargs='?',
            type=str,
            help=_(
                'The path to the archive containing the legacy site logs to '
                'import.'
            )
        )

    def handle(self, *args, **options):

        count = 0
        prep_less = 0
        prep_eq = 0
        prep_more = 0
        no_prep = 0
        unresolved = set()
        if not options['file']:
            file_path = os.path.expanduser(input(_('Archive tar file path: ')))
        else:
            file_path = os.path.expanduser(options['file'])

        if not os.path.exists(file_path):
            raise CommandError(_(f'{file_path} is not a file.'))

        with transaction.atomic():
            with tarfile.open(file_path, "r") as archive:
                with tqdm(
                    total=len(archive.getnames()),
                    desc='Importing',
                    unit='logs',
                    postfix={'log': ''}
                ) as p_bar:
                    for member in archive.getmembers():
                        if not member.isfile():
                            continue
                        
                        count += 1
                        archive_name = os.path.basename(member.name)

                        match = FILE_NAME_REGEX.match(archive_name)
                        if not match:
                            p_bar.update(n=1)
                            unresolved.add(archive_name)
                            continue

                        four_id = match.group(1)
                        time_part = match.group(2)
                        no_day = False
                        if len(time_part) == 4:
                            no_day = True
                            year = int(time_part[:2])
                            if year > 80:
                                year += 1900
                            else:
                                year += 2000
                            month = int(time_part[2:])
                            log_date = date(year=year, month=month, day=1)
                        else:
                            log_date = parser.parse(time_part).date()

                        try:
                            site = Site.objects.get(name__istartswith=four_id)

                            """
                            archive_name = f'{site.name.upper()}_' \
                                           f'{log_date.year}' \
                                           f'{log_date.month:02}' \
                                           f'{log_date.day:02}.' \
                                           f'{SiteLogFormat.LEGACY.ext}'
                            """
                            
                            log_str = archive.extractfile(member).read()
                            params, prep_date = self.log_params(log_str, site)

                            log_time = make_aware(datetime(
                                year=log_date.year,
                                month=log_date.month,
                                day=log_date.day,
                                hour=0,
                                minute=0,
                                second=0
                            ), utc)

                            if prep_date:
                                # use the prep date if it agrees with a lower
                                # resolution log_date (i.e. no day - old style)
                                if (
                                    prep_date.month == log_time.month and
                                    prep_date.year == log_time.year and
                                    no_day
                                ):
                                    log_time = make_aware(datetime(
                                        year=prep_date.year,
                                        month=prep_date.month,
                                        day=prep_date.day,
                                        hour=0,
                                        minute=0,
                                        second=0
                                    ), utc)
                                if prep_date < log_date:
                                    prep_less += 1
                                if prep_date == log_date:
                                    prep_eq += 1
                                if prep_date > log_date:
                                    prep_more += 1
                            else:
                                no_prep += 1

                            if (
                                log_date and
                                site.join_date is None or
                                site.join_date > log_time.date()
                            ):
                                site.join_date = log_time.date()
                                site.save()

                            index = ArchiveIndex.objects.insert_index(
                                site=site,
                                begin=log_time
                            )

                            ArchivedSiteLog.objects.get_or_create(
                                index=index,
                                log_format=SiteLogFormat.LEGACY,
                                defaults={
                                    'site': site,
                                    'name': archive_name,
                                    'file_type': SLMFileType.SITE_LOG,
                                    'file': ContentFile(
                                        log_str,
                                        name=archive_name
                                    )
                                }
                            )

                        except Site.DoesNotExist:
                            unresolved.add(archive_name)

                        p_bar.set_postfix({'log': archive_name})
                        p_bar.update(n=1)

        print(
            f'Unresolved files: {len(unresolved)}\n'
            f'Total Imports: {count}\n'
            f'prep_time<({prep_less/count * 100:.04}%)\n'
            f'prep_time=({prep_eq/count * 100:.04}%)\n'
            f'prep_time>({prep_more/count * 100:.04}%)\n'
            f'prep_time=None({no_prep/count * 100:.04}%)\n'
        )

    def log_params(self, log_str, site):
        bound_log = SiteLogBinder(
            SiteLogParser(
                self.decode_str(log_str),
                site_name=site.name
            )
        ).parsed

        def get_param(section_index, field_name, null_val=None):
            binding = getattr(
                getattr(bound_log, 'sections', {}).get(section_index, {}),
                'binding',
                {}
            )
            if binding:
                return binding.get(field_name, null_val)
            return null_val

        def lat_lng(lat_lng):
            if lat_lng is not None:
                return dddmmssss_to_decimal(lat_lng)
            return None

        prep_time = get_param((0, None, None), 'date_prepared')
        if prep_time:
            prep_time = datetime(
                year=prep_time.year,
                month=prep_time.month,
                day=prep_time.day,
                tzinfo=utc
            )

        params = {
            'latitude': lat_lng(get_param((2, None, None), 'latitude')),
            'longitude': lat_lng(get_param((2, None, None), 'longitude')),
            'elevation': get_param((2, None, None), 'elevation'),
            # 'llh': (
            #     lat_lng(get_param((2, None, None), 'latitude')),
            #     lat_lng(get_param((2, None, None), 'longitude')),
            #     get_param((2, None, None), 'elevation')
            # ),
            'city': get_param((2, None, None), 'city', ''),
            'country': get_param((2, None, None), 'country'),
            'antenna': None,
            'radome': None,
            'receiver': None,
            'serial_number': '',
            'firmware': '',
            'frequency_standard': None,
            'domes_number': get_param((1, None, None), 'iers_domes_number', ''),
            'satellite_system': [],
            'data_center': get_param((13, None, None), 'primary', '')
        }
        for index, section in bound_log.sections.items():
            if index[0] == 3 and section.contains_values and section.binding:
                params['receiver'] = Receiver.objects.filter(
                    model=section.binding.get('receiver_type', None)
                ).first()
                params['serial_number'] = section.binding.get(
                    'serial_number',
                    ''
                )
                params['firmware'] = section.binding.get('firmware', '')
                params['satellite_system'] = section.binding.get(
                    'satellite_system',
                    None
                )
            if index[0] == 4 and section.contains_values and section.binding:
                params['antenna'] = Antenna.objects.filter(
                    model=section.binding.get('antenna_type', None)
                ).first()
                params['radome'] = Radome.objects.filter(
                    model=section.binding.get('radome_type', None)
                ).first()

            if index[0] == 6 and section.contains_values and section.binding:
                params['frequency_standard'] = section.binding.get(
                    'standard_type',
                    None
                )
        return params, prep_time

    def decode_str(self, log_str):
        try:
            return log_str.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return log_str.decode('ascii')
            except UnicodeDecodeError:
                return log_str.decode('latin')
