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
    SiteIndex,
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
from datetime import datetime
from django.utils.timezone import utc, make_aware


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
                        name = os.path.basename(member.name)
                        if '_' not in name:
                            p_bar.update(n=1)
                            unresolved.add(name)
                            continue
                        parts = re.split('[._-]', name)
                        four_id = parts[0]
                        try:
                            log_time = make_aware(parser.parse(parts[1]), utc)
                        except parser.ParserError:
                            #print(f'Invalid log name: {name}')
                            continue

                        try:
                            site = Site.objects.get(name__istartswith=four_id)
                            
                            archive_name = f'{site.name.upper()}_' \
                                           f'{log_time.year}' \
                                           f'{log_time.month:02}' \
                                           f'{log_time.day:02}.' \
                                           f'{SiteLogFormat.LEGACY.ext}'
                            
                            log_str = archive.extractfile(member).read()
                            params, prep_time = self.log_params(log_str, site)

                            if prep_time:
                                # todo - what is correct when these don't match?
                                if prep_time < log_time:
                                    prep_less += 1
                                if prep_time == log_time:
                                    prep_eq += 1
                                if prep_time > log_time:
                                    prep_eq += 1
                            else:
                                no_prep += 1

                            sat_sys = params.pop('satellite_system', [])
                            to_long = set()
                            for param, value in params.items():
                                if value and isinstance(value, str):
                                    field = SiteIndex._meta.get_field(param)
                                    if len(value) > getattr(
                                        field, 'max_length', 999999
                                    ):
                                        #print(
                                        #    f'Value too long: [{param}]: '
                                        #    f'{value}'
                                        #)
                                        to_long.add(param)
                            index = SiteIndex.objects.insert_index(
                                site=site,
                                begin=log_time,
                                **{
                                    param: val for param, val in params.items()
                                    if param not in to_long
                                }
                            )
                            if sat_sys:
                                index.satellite_system.set(sat_sys)

                            ArchivedSiteLog.objects.create(
                                site=site,
                                name=archive_name,
                                index=index,
                                file_type=SLMFileType.SITE_LOG,
                                log_format=SiteLogFormat.LEGACY,
                                file=ContentFile(log_str, name=archive_name)
                            )

                        except Site.DoesNotExist:
                            unresolved.add(name)

                        p_bar.set_postfix({'log': name})
                        p_bar.update(n=1)

        print(
            f'Unresolved files: {len(unresolved)}\n'
            f'Total Imports: {count}\n'
            f'prep_time<({prep_less/count * 100:.04}%)\n'
            f'prep_time=({prep_eq/count * 100:.04}%)\n'
            f'prep_time>({prep_more/count * 100:.04}%)\n'
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
                return lat_lng / 10000
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
                    pk=section.binding.get('receiver_type', None)
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
                    pk=section.binding.get('antenna_type', None)
                ).first()
                params['radome'] = Radome.objects.filter(
                    pk=section.binding.get('radome_type', None)
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
