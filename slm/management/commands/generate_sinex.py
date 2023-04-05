"""
Update the data availability information for each station.
"""
from django.core.management import BaseCommand, CommandError
from slm.models import Site, SiteReceiver, SiteAntenna, Network
from django.utils.translation import gettext as _
import requests
import logging
import re
from datetime import datetime
from slm.utils import dddmmss_ss_parts, xyz2llh
from collections import defaultdict
from slm.defines import ISOCountry
from django.db.models import Prefetch
import html
import zlib

DEFAULT_ANTEX = 'https://files.igs.org/pub/station/general/igs20.atx.gz'


def rec_dd():
    return defaultdict(rec_dd)


sinex_code = ''
siteAnt = rec_dd()
used_antennas = set()
atx = rec_dd()
sat_phase_center = rec_dd()


def sinex_time(time):
    if time is None:
        return '00:000:00000'
    return f'{time.strftime("%y:%j")}:' \
           f'{time.hour * 60 * 60 + time.minute * 60 + time.second:05.0f}'


def date2YYdoy(date):
    if date == '' or 'CCYY' in date:
        return 0, 0, 0

    hour = minute = _sec = int(0)
    m = re.match(
        r'(\d\d\d\d)-(\d\d)-(\d\d)((\s|T)(\d\d):(\d\d)(Z|\d\d.\d\d\d\d\d)?)?',
        date
    )
    if m:
        year = int(m.group(1))
        mo = int(m.group(2))
        day = int(m.group(3))
        if m.group(4):
            hour = int(m.group(6))
            minute = int(m.group(7))
            if m.group(8):
                if m.group(8) == "Z":
                    _sec = 0
                else:
                    _sec = float(m.group(9))

        second = hour * 60 * 60 + minute * 60 + _sec

        _date = "%4d-%02d-%02d %02d:%02d" % (year, mo, day, hour, minute)
        dateObj = datetime.strptime(_date, "%Y-%m-%d %H:%M")
        _y, _doy = dateObj.strftime("%y %j").split()

    return int(_y), int(_doy), int(second)


class Command(BaseCommand):
    help = 'Generate the sinex files for each station.'

    logger = logging.getLogger(__name__ + '.Command')

    def add_arguments(self, parser):

        parser.add_argument(
            'destination',
            metavar='D',
            nargs='?',
            type=str,
            help=_(
                'The destination to write the sinex file to, if none '
                'provided will print to stdout.'
            )
        )

        parser.add_argument(
            '--antex-file',
            dest='antex_file',
            default=DEFAULT_ANTEX,
            type=str,
            help=_('The antex file to use. Default: %s') % (
                DEFAULT_ANTEX,
            )
        )

        parser.add_argument(
            '--include-network',
            dest='include_networks',
            action='append',
            default=[],
            help=_(
                'Include non-public sites in the given networks.'
            )
        )

        parser.add_argument(
            '--include-former',
            dest='include_former',
            action='store_true',
            default=False,
            help=_(
                'Include former sites in the list.'
            )
        )

    def handle(self, *args, **options):
        global used_antennas

        sites = Site.objects.all().order_by('name')
        sites = sites.public() if options['include_former'] else sites.active()
        networks = [
            Network.objects.get(name__iexact=network)
            for network in options['include_networks']
        ]
        if networks:
            sites |= sites.filter(networks__in=networks)

        sites = sites.distinct()

        used_antennas = set([
            "%-16s%-4s" % (ant[0], ant[1]) for ant in
            SiteAntenna.objects.filter(site__in=sites).order_by(
                'antenna_type'
            ).values_list(
                'antenna_type__model',
                'radome_type__model'
            ).distinct('antenna_type__model', 'radome_type__model')
        ])

        self.build_antex_index(options['antex_file'])

        output = self.stdout
        if options['destination']:
            output = open(options['destination'], 'w')

        # write header
        for line in self.header(options['antex_file']):
            output.write(f'{line}\n')

        # write SITE/ID section
        for line in self.site_ids(sites):
            output.write(f'{line}\n')

        # write SITE/RECEIVER section
        for line in self.site_receivers(sites):
            output.write(f'{line}\n')

        # write SITE/ANTENNA section
        for line in self.site_antennas(sites):
            output.write(f'{line}\n')

        # write GPS/PHASECENTER section
        for line in self.gps_phase_center():
            output.write(f'{line}\n')

        # write GAL/PHASECENTER section
        for line in self.gal_phase_center():
            output.write(f'{line}\n')

        # write SITE/ECCENTRICITY
        for line in self.site_eccentricity(sites):
            output.write(f'{line}\n')

        # write SATELLITE/ID
        for line in self.satellite_ids():
            output.write(f'{line}\n')

        # write +SATELLITE/PHASE_CENTER
        for line in self.satellite_phase_centers():
            output.write(f'{line}\n')

        # close out the file
        for line in self.footer():
            output.write(f'{line}\n')

        if options['destination']:
            output.close()

    def header(self, antex_file):
        global sinex_code
        now = datetime.now()
        now_date = "%04d-%02d-%02dT%02d:%02d:%02d" % (
            now.year, now.month, now.day, now.hour, now.minute, now.second
        )
        now_year, now_jday, now_seconds = date2YYdoy(now_date)

        yield (
                '%%=SNX 2.02 IGS %02d:%03d:%05d IGS 00:000:00000 00:000:00000 P '
                '00000 0' % (now_year, now_jday, now_seconds)
        )
        yield '+FILE/REFERENCE'
        yield ' DESCRIPTION        IGS Central Bureau'
        yield ' OUTPUT             historical sinex header file'
        yield ' CONTACT            cb@igs.org'
        yield ' SOFTWARE           SLM2SNX'
        yield ' HARDWARE           x86_64 Linux | AWS Cloud'
        yield f' INPUT              SiteLog Manager, {sinex_code.lower()}.atx'
        yield '-FILE/REFERENCE'
        yield '+FILE/COMMENT'
        yield ' This file is generated daily from all current IGS site logs in'
        yield '    https://files.igs.org/pub/station/log/'
        yield (
            ' Phase center offsets are a function of antenna type, using as '
            'reference'
        )
        yield f'    {antex_file.rstrip(".gz")}'
        yield '-FILE/COMMENT'
        yield '+INPUT/ACKNOWLEDGMENTS'
        yield ' IGS International GNSS Service'
        yield '-INPUT/ACKNOWLEDGMENTS'

    def footer(self):
        yield '%ENDSNX'

    def site_ids(self, sites):
        sites = sites.with_location_fields().with_identification_fields()
        yield '+SITE/ID'
        yield (
            '*CODE PT __DOMES__ T _STATION DESCRIPTION__ _LONGITUDE_ '
            '_LATITUDE__ HEIGHT_'
        )
        for site in sites:
            ctry = html.unescape((
                site.country.short_name
                if isinstance(site.country, ISOCountry)
                else site.country
            ))
            llh = xyz2llh(site.xyz.coords)
            location = html.unescape(
                f'{site.city or site.state}'
                f'{"," if site.city or site.state else ""}{ctry}'
            )[:21]
            lat_deg, lat_min, lat_sec = dddmmss_ss_parts(llh[0])

            if lat_deg is None:
                continue

            # is sinex longitude 0-360 or -180 to 180?
            lon_deg, lon_min, lon_sec = dddmmss_ss_parts(
                llh[1] if llh[1] > 0 else llh[1] + 360
            )

            yield f' {site.four_id.lower()}  A ' \
                  f'{site.iers_domes_number:>9} P ' \
                  f'{location:<21}  {lon_deg:3d} {lon_min:2d} ' \
                  f'{lon_sec:>4.1f} {lat_deg:3d} {lat_min:2d} ' \
                  f'{lat_sec:>4.1f} {llh[2]:>7.1f}'
        yield '-SITE/ID'

    def site_receivers(self, sites):

        yield '+SITE/RECEIVER'
        yield (
            '*CODE PT SOLN T _DATA START_ __DATA_END__ ___RECEIVER_TYPE____ '
            '_S/N_ _FIRMWARE__'
        )

        for site in sites.prefetch_related(
                Prefetch(
                    'sitereceiver_set',
                    queryset=SiteReceiver.objects.published().prefetch_related(
                        'receiver_type'
                    ).order_by('installed')
                )
        ):
            for receiver in site.sitereceiver_set.all():
                yield (
                    f' {site.four_id.lower()}  A ---- P '
                    f'{sinex_time(receiver.installed):<12.12} '
                    f'{sinex_time(receiver.removed):<12.12} '
                    f'{receiver.receiver_type.model:<20.20} '
                    f'{receiver.serial_number:<5.5} {receiver.firmware:<11.11}'
                )
        yield '-SITE/RECEIVER'

    def site_antennas(self, sites):
        yield '+SITE/ANTENNA'
        yield (
            '*CODE PT SOLN T _DATA START_ __DATA_END__ ____ANTENNA_TYPE____ '
            '_S/N_ _DAZ'
        )
        for site in sites.prefetch_related(
                Prefetch(
                    'siteantenna_set',
                    queryset=SiteAntenna.objects.published().prefetch_related(
                        'antenna_type',
                        'radome_type'
                    ).order_by('installed')
                )
        ):
            for antenna in site.siteantenna_set.all():
                yield (
                    f' {site.four_id.lower()}  A ---- P '
                    f'{sinex_time(antenna.installed):<12.12} '
                    f'{sinex_time(antenna.removed):<12.12} '
                    f'{antenna.antenna_type.model:<15.15} '
                    f'{antenna.radome_type.model:4.4} '
                    f'{antenna.serial_number:<5.5} '
                    f'{antenna.alignment if antenna.alignment else 0.0:>4.0f}'
                )
                # todo: add antenna offset defaulting to zero if its unknown?
                #  seems wrong
        yield '-SITE/ANTENNA'

    def gps_phase_center(self):
        global siteAnt
        yield '+SITE/GPS_PHASE_CENTER'
        yield (
            '*ANTENNA_NAME____DOME S_NO_ __UP__ NORTH_ _EAST_ __UP__ NORTH_ '
            '_EAST_ ANT_MODEL_'
        )
        for ant in sorted(siteAnt):
            if "G02" in siteAnt[ant]:
                yield (
                    f' {ant:20} ----- {siteAnt[ant]["G01"]["up"]:6.6} '
                    f'{siteAnt[ant]["G01"]["north"]:6.6} '
                    f'{siteAnt[ant]["G01"]["east"]:6.6} '
                    f'{siteAnt[ant]["G02"]["up"]:6.6} '
                    f'{siteAnt[ant]["G02"]["north"]:6.6} '
                    f'{siteAnt[ant]["G02"]["east"]:6.6} {sinex_code:10.10}'
                )
            else:
                yield (
                    f' {ant:20} ----- {siteAnt[ant]["G01"]["up"]:6.6} '
                    f'{siteAnt[ant]["G01"]["north"]:6.6} '
                    f'{siteAnt[ant]["G01"]["east"]:6.6} ------ ------ ------ '
                    f'{sinex_code:10.10}'
                )
        yield '-SITE/GPS_PHASE_CENTER'

    def gal_phase_center(self):
        global siteAnt
        yield '+SITE/GAL_PHASE_CENTER'
        yield (
            '*ANTENNA_NAME____DOME S_NO_ __UP__ NORTH_ _EAST_ __UP__ NORTH_ '
            '_EAST_ ANT_MODEL_'
        )
        for ant in sorted(siteAnt):
            if 'E01' in siteAnt[ant]:
                _e01 = f'{siteAnt[ant]["E01"]["up"]:6.6} ' \
                       f'{siteAnt[ant]["E01"]["north"]:6.6} ' \
                       f'{siteAnt[ant]["E01"]["east"]:6.6}'
            else:
                _e01 = '------ ------ ------'
            if 'E05' in siteAnt[ant]:
                _e05 = f'{siteAnt[ant]["E05"]["up"]:6.6} ' \
                       f'{siteAnt[ant]["E05"]["north"]:6.6} ' \
                       f'{siteAnt[ant]["E05"]["east"]:6.6}'
            else:
                _e05 = '------ ------ ------'
            yield f' {ant} ----  {_e01} {_e05} {sinex_code:10s}'

            if "E06" in siteAnt[ant]:
                _e06 = f'{siteAnt[ant]["E06"]["up"]:6.6} ' \
                       f'{siteAnt[ant]["E06"]["north"]:6.6} ' \
                       f'{siteAnt[ant]["E06"]["east"]:6.6}'
            else:
                _e06 = '------ ------ ------'
            if "E07" in siteAnt[ant]:
                _e07 = f'{siteAnt[ant]["E07"]["up"]:6.6} ' \
                       f'{siteAnt[ant]["E07"]["north"]:6.6} ' \
                       f'{siteAnt[ant]["E07"]["east"]:6.6}'
            else:
                _e07 = '------ ------ ------'
            yield f' {ant} ----  {_e06} {_e07} {sinex_code:10s}'

            if "E08" in siteAnt[ant]:
                _e08 = f'{siteAnt[ant]["E08"]["up"]:6.6} ' \
                       f'{siteAnt[ant]["E08"]["north"]:6.6} ' \
                       f'{siteAnt[ant]["E08"]["east"]:6.6}'
            else:
                _e08 = '------ ------ ------'

            yield f' {ant} ----  {_e08} ------ ------ ------ {sinex_code:10s}'
        yield '-SITE/GAL_PHASE_CENTER'

    def site_eccentricity(self, sites):
        yield '+SITE/ECCENTRICITY'
        yield (
            '*CODE PT SOLN T _DATA START_ __DATA_END__ REF __DX_U__ __DX_N__ '
            '__DX_E__'
        )
        for site in sites.prefetch_related(
                Prefetch(
                    'siteantenna_set',
                    queryset=SiteAntenna.objects.published().order_by(
                        'installed')
                )
        ):
            for antenna in site.siteantenna_set.all():
                yield (
                    f' {site.four_id.lower():4.4}  A ---- P '
                    f'{sinex_time(antenna.installed):12.12} '
                    f'{sinex_time(antenna.removed):12.12} UNE '
                    f'{antenna.marker_enu[2]:8.4f} '
                    f'{antenna.marker_enu[1]:8.4f} '
                    f'{antenna.marker_enu[0]:8.4f}'
                )
        yield '-SITE/ECCENTRICITY'

    def satellite_ids(self):
        global atx
        yield '+SATELLITE/ID'
        yield (
            '*CNNN PN COSPARID_ T _START_DATE_ __END_DATE__ '
            '____ANTENNA_TYPE____'
        )
        for sat in sorted(atx):
            for startDate in atx[sat]:
                yield (
                    f' {sat:.4s} {atx[sat][startDate]["prn"]:.2s} '
                    f'{atx[sat][startDate]["cospar_id"]:.9s} P '
                    f'{startDate:.12s} {atx[sat][startDate]["endDate"]:.12s} '
                    f'{atx[sat][startDate]["name"]:.20s}'
                )
        yield '-SATELLITE/ID'

    def satellite_phase_centers(self):
        global sat_phase_center
        yield '+SATELLITE/PHASE_CENTER'
        yield (
            '*CNNN F __UP__ NORTH_ _EAST_ F __UP__ NORTH_ _EAST_ ' \
            'SINEXCODE_ V M'
        )
        for sat in sorted(sat_phase_center):
            if sat.startswith('G'):
                yield (
                    f' {sat:4.4} 1 {sat_phase_center[sat]["G01"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["G01"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["G01"]["east"]:6.6} 2 '
                    f'{sat_phase_center[sat]["G02"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["G02"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["G02"]["east"]:6.6} '
                    f'{sinex_code:10.10} A E'
                )
                try:
                    yield (
                        f' {sat:4.4} 5 '
                        f'{sat_phase_center[sat]["G05"]["up"]:6.6} '
                        f'{sat_phase_center[sat]["G05"]["north"]:6.6} '
                        f'{sat_phase_center[sat]["G05"]["east"]:6.6} - ------ '
                        f'------ ------ {sinex_code:10.10} A E'
                    )
                except:
                    pass

            if sat.startswith('R'):
                yield (
                    f' {sat:4.4} 1 {sat_phase_center[sat]["R01"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["R01"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["R01"]["east"]:6.6} 2 '
                    f'{sat_phase_center[sat]["R02"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["R02"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["R02"]["east"]:6.6} '
                    f'{sinex_code:10.10} A E'
                )

            if sat.startswith('E'):
                yield (
                    f' {sat:4.4} 1 {sat_phase_center[sat]["E01"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["E01"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["E01"]["east"]:6.6} 5 '
                    f'{sat_phase_center[sat]["E05"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["E05"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["E05"]["east"]:6.6} '
                    f'{sinex_code:10.10} A E'
                )
                yield (
                    f' {sat:4.4} 6 {sat_phase_center[sat]["E06"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["E06"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["E06"]["east"]:6.6} 7 '
                    f'{sat_phase_center[sat]["E07"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["E07"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["E07"]["east"]:6.6} '
                    f'{sinex_code:10.10} A E'
                )
                yield (
                    f' {sat:4.4} 8 '
                    f'{sat_phase_center[sat]["E08"]["up"]:6.6} '
                    f'{sat_phase_center[sat]["E08"]["north"]:6.6} '
                    f'{sat_phase_center[sat]["E08"]["east"]:6.6} - ------ '
                    f'------ ------ {sinex_code:10.10} A E'
                )
        yield '-SATELLITE/PHASE_CENTER'

    def build_antex_index(self, antex_file):
        """
        Streams the antex file from files.igs.org and builds an index off of
        it.

        :param antex_file: The url to the antex file to use, may be gzipped or
            uncompressed.
        """
        global sinex_code
        global siteAnt
        global atx
        global sat_phase_center

        def process_line(
                line,
                prn=None,
                svn=None,
                name=None,
                cospar_id=None,
                north=None,
                east=None,
                up=None,
                atxStartDate=None,
                atxEndDate=None,
                sat_num=None
        ):
            global sinex_code
            global siteAnt
            global atx
            global sat_phase_center

            if 'TYPE / SERIAL NO' in line:
                name = line[0:20].rstrip()
                prn = line[21:23]
                svn = line[40:44]
                cospar_id = line[50:59]
                atxEndDate = "00:000:00000"

            if 'SINEX CODE' in line[60:]:
                sinex_code = line[:10]

            if 'VALID FROM' in line:
                year, month, day, hour, minute, second = line[0:60].split()
                yy, doy, sec = date2YYdoy(
                    "%04d-%02d-%02d %02d:%02d:%02d" % (
                        int(year), int(month), int(day), int(hour),
                        int(minute), int(float(second))))
                atxStartDate = "%02d:%03d:%05d" % (
                    int(yy), int(doy), int(sec))

            if 'VALID UNTIL' in line:
                year, month, day, hour, minute, second = line[0:60].split()
                yy, doy, sec = date2YYdoy(
                    "%04d-%02d-%02d %02d:%02d:%02d" % (
                        int(year), int(month), int(day), int(hour),
                        int(minute), int(float(second))))
                atxEndDate = "%02d:%03d:%05d" % (
                    int(yy), int(doy), int(sec))

            if 'START OF FREQUENCY' in line[60:]:
                sat_num = line[0:59].split()

            if 'NORTH / EAST / UP' in line[60:]:
                north, east, up = line[0:60].split()
                north = float(north) / 1000
                east = float(east) / 1000
                up = float(up) / 1000

                if prn.isspace():
                    if name in used_antennas:
                        if north < 0:
                            siteAnt[name][sat_num[0]][
                                "north"] = re.sub("-0.", "-.",
                                                  "%6.4f" % north)
                        else:
                            siteAnt[name][sat_num[0]]["north"] = str(
                                "%6.4f" % north)
                        if east < 0:
                            siteAnt[name][sat_num[0]]["east"] = re.sub(
                                "-0.", "-.", "%6.4f" % east)
                        else:
                            siteAnt[name][sat_num[0]]["east"] = str(
                                "%6.4f" % east)
                        if up < 0:
                            siteAnt[name][sat_num[0]]["up"] = re.sub(
                                "-0.", "-.", "%6.4f" % up)
                        else:
                            siteAnt[name][sat_num[0]]["up"] = str("%6.4f" % up)

                        # siteAnt[name][sat_num[0]]["north"] = re.sub("0.", ".", str(north), 1)
                        # siteAnt[name][sat_num[0]]["east"] = re.sub("0.", ".", str(east), 1)
                        # siteAnt[name][sat_num[0]]["up"] = re.sub("0.", ".", str(up), 1)
                else:
                    # satAnt
                    atx[svn][atxStartDate]["endDate"] = atxEndDate
                    atx[svn][atxStartDate]["svn"] = svn
                    atx[svn][atxStartDate]["prn"] = prn
                    atx[svn][atxStartDate]["north"] = north
                    atx[svn][atxStartDate]["east"] = east
                    atx[svn][atxStartDate]["up"] = up
                    atx[svn][atxStartDate]["cospar_id"] = cospar_id
                    atx[svn][atxStartDate]["name"] = name

                    if north < 0:
                        sat_phase_center[svn][sat_num[0]]["north"] = re.sub(
                            "-0.", '-.', "%6.4f" % north
                        )
                    else:
                        sat_phase_center[svn][sat_num[0]]["north"] = str(
                            "%6.4f" % north
                        )
                    if east < 0:
                        sat_phase_center[svn][sat_num[0]]["east"] = re.sub(
                            "-0.", '-.', "%6.4f" % east
                        )
                    else:
                        sat_phase_center[svn][sat_num[0]]["east"] = str(
                            "%6.4f" % east
                        )
                    if up < 0:
                        sat_phase_center[svn][sat_num[0]]["up"] = re.sub(
                            "-0.", '-.', "%6.4f" % up
                        )
                    else:
                        sat_phase_center[svn][sat_num[0]]["up"] = str(
                            "%6.4f" % up
                        )

            if 'END OF ANTENNA' in line:
                return []
            return [
                prn, svn, name, cospar_id, north, east, up,
                atxStartDate, atxEndDate, sat_num
            ]

        resp = requests.get(antex_file, stream=True)
        if resp.status_code < 300:
            last = ''
            decomp = None
            if resp.headers['content-type'].endswith('gzip'):
                decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)

            params = []
            for chunk in resp.iter_content(chunk_size=4096):
                if not chunk:
                    if last:
                        process_line(last, *params)
                if decomp:
                    chunk = decomp.decompress(chunk)

                chunk = chunk.decode('utf-8')
                lines = chunk.split('\n')
                lines[0] = last + lines[0]
                last = lines[-1]
                for line in lines[0:-1]:
                    params = process_line(line, *params)
        else:
            raise CommandError(
                f'Unable to fetch antex file ({antex_file}):'
                f'{resp.status_code} {resp.reason}'
            )
