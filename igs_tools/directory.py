import argparse
from dateutil import parser as date_parser
from datetime import datetime, timedelta, date
from igs_tools.defines import RinexVersion, DataCenter, DataRate
from igs_tools.utils import classproperty
from typing import Optional, Generator, Union
from pathlib import Path
from igs_tools.connection import Connection
from igs_tools.utils import get_file_properties


class Listing:

    station: str
    protocol: str
    domain: str
    port: int
    filename: str
    directory: str
    rinex_version: RinexVersion
    data_rate: DataRate
    date: Union[date, datetime]
    data_center: DataCenter
    size: Optional[int]
    file_type: str

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def path(self):
        return Path(self.directory) / self.filename


class DirectoryListing:

    data_centers = [center for center in DataCenter]
    rinex_versions = [RinexVersion.v3]
    data_rates = [DataRate.DAILY]

    username = ''
    password = ''

    @classproperty
    def start(self):
        return datetime.now().date()

    @classproperty
    def end(self):
        return datetime.now().date()

    def __init__(
        self,
        stations=None,
        data_centers=None,
        rinex_versions=None,
        data_rates=None,
        start=None,
        end=None,
        dates=None,
        username=username,
        password=password
    ):
        self.stations = set([stn.lower()[0:4] for stn in stations or []])
        self.data_centers = set(data_centers or self.data_centers)
        self.rinex_versions = set(rinex_versions or self.rinex_versions)
        self.data_rates = set(data_rates or self.data_rates)

        if dates and (start or end):
            raise ValueError('Cannot specify dates and start/end.')

        self.start = start or self.start
        self.end = end or self.end
        if self.start < self.end:
            # allow any order
            self.start, self.end = self.end, self.start
        self.dates = dates or [
            self.end + timedelta(days=i)
            for i in range((self.start - self.end).days + 1)
        ]
        self.username = username
        self.password = password

    def __iter__(self) -> Generator[Listing, None, None]:
        visited = set()
        for data_center in self.data_centers:
            connection = Connection(data_center, self.username, self.password)
            print(data_center)
            for rinex_version in self.rinex_versions:
                print(rinex_version)
                for data_rate in self.data_rates:
                    print(data_rate)
                    for date in self.dates:
                        print(date)
                        path = data_center.directory(
                            rinex_version,
                            data_rate,
                            date
                        )
                        print(path)
                        if not path or path in visited:
                            continue
                        visited.add(path)
                        for filename in connection.list(path):
                            properties = get_file_properties(filename)
                            if (
                                properties is None or
                                properties['rinex_version']
                                    not in self.rinex_versions or (
                                    self.stations and
                                    properties['station'].lower()[0:4]
                                        not in self.stations
                                )
                            ):
                                continue
                            yield Listing(
                                station=properties['station'],
                                protocol=data_center.protocol,
                                domain=data_center.domain,
                                port=data_center.port,
                                filename=filename,
                                directory=path,
                                rinex_version=properties['rinex_version'],
                                data_rate=data_rate,
                                date=date,
                                file_type=properties['file_type'],
                                size=properties.get('size', None),
                                data_center=data_center
                            )


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Fetch directory information about IGS RINEX files.'
    )
    parser.add_argument(
        'stations',
        metavar='S',
        type=str,
        nargs='*',
        default=[],
        help='The stations to fetch directory listings for. Default: all'
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '--date',
        dest='dates',
        action='append',
        default=[],
        type=lambda s: date_parser.parse(s).date(),
        help='The date(s) to fetch directory listings for.'
    )

    group.add_argument(
        '-s',
        '--start',
        dest='start',
        type=lambda s: date_parser.parse(s).date(),
        default=None,
        help=f'The start date (inclusive) to fetch directory listings for. '
             f'Default: {DirectoryListing.start}'
    )

    parser.add_argument(
        '-e',
        '--end',
        dest='end',
        type=lambda s: date_parser.parse(s).date(),
        default=None,
        help='The end date (inclusive) to fetch directory listings for. '
             'Default: {DirectoryListing.start}'
    )

    parser.add_argument(
        '-d',
        '--data-center',
        dest='data_centers',
        action='append',
        default=[],
        type=DataCenter,
        choices=[center.label for center in DataCenter],
        help=f'The list of data centers to fetch directory listings from.'
             f'Default: {[center.label for center in DataCenter]}'
    )

    parser.add_argument(
        '-v',
        '--version',
        dest='rinex_versions',
        action='append',
        default=[],
        type=RinexVersion,
        choices=[rinex.slug for rinex in RinexVersion.major_versions()],
        help=f'The rinex version of the files to list. '
             f'Default: {DirectoryListing.rinex_versions}'
    )

    parser.add_argument(
        '-r',
        '--rate',
        dest='data_rates',
        action='append',
        default=[],
        type=DataRate,
        choices=[rate.slug for rate in DataRate],
        help=f'The data rates of the files to list. '
             f'Default: {DirectoryListing.data_rates}'
    )

    parser.add_argument(
        '--username',
        dest='username',
        type=str,
        help='The username to use for authentication if necessary.',
        default=''
    )

    parser.add_argument(
        '--password',
        dest='password',
        type=str,
        help='The password to use for authentication if necessary.',
        default=''
    )

    args = parser.parse_args()

    for listing in DirectoryListing(
        stations=args.stations,
        data_centers=args.data_centers,
        rinex_versions=args.rinex_versions,
        data_rates=args.data_rates,
        start=args.start,
        end=args.end or args.start,
        dates=args.dates,
        username=args.username,
        password=args.password
    ):
        print(
            f'{listing.station.upper()} {listing.rinex_version} '
            f'{listing.data_rate} {listing.date} {listing.filename} '
            f'{str(listing.data_center)} {listing.size}'
        )
