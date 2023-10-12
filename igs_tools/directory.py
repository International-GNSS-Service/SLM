import argparse
from dateutil import parser as date_parser
from datetime import datetime, timedelta, date
from igs_tools.defines import RinexVersion, DataCenter, DataRate, DataType
from igs_tools.utils import classproperty, chunks
from typing import Optional, Generator, Union, Dict, Set, List
from pathlib import Path
from igs_tools.connection import Connection
from igs_tools.file import GNSSDataFile
from itertools import product
import asyncio
import logging


class Listing:

    protocol: str
    domain: str
    port: int
    file: Union[str, GNSSDataFile]
    directory: str
    size: Optional[int]
    data_center: DataCenter

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def path(self):
        return Path(self.directory) / self.file

    @property
    def is_gnss_data(self):
        return isinstance(self.file, GNSSDataFile)


class DirectoryListing:

    data_centers = DataCenter.global_centers
    rinex_versions = [RinexVersion.v3]
    data_rates = DataRate.DAILY
    data_types = DataType.MIXED_OBS
    hours = [1]

    username = ''
    password = ''

    connections_: Dict[DataCenter, Connection]
    visited = Set

    logger = logging.getLogger(__name__)

    queue = asyncio.Queue()

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
        data_types=None,
        hours=None,
        start=None,
        end=None,
        dates=None,
        username=username,
        password=password,
        async_queues=None
    ):
        self.stations = set([stn.lower()[0:4] for stn in stations or []])
        self.data_centers = set(data_centers or self.data_centers)
        self.rinex_versions = set(rinex_versions or self.rinex_versions)
        self.data_rates = set(data_rates or self.data_rates)
        self.data_types = set(data_types or self.data_types)
        self.hours = set(hours or self.hours)
        self.connections_ = {}
        self.visited = set()

        # by default, we want to use the same number of queues as data centers
        self.async_queues = async_queues or len(self.data_centers)

        if dates and (start or end):
            raise ValueError('Cannot specify dates and start/end.')

        self.start = start or self.start
        self.end = end or self.end
        if self.start < self.end:
            # allow any order
            self.start, self.end = self.end, self.start
        self.dates = dates or [  # todo should be a generator, could be large
            self.end + timedelta(days=i)
            for i in range((self.start - self.end).days + 1)
        ]
        self.username = username
        self.password = password

    async def read_dir(
        self,
        hour: int,
        data_type: DataType,
        date: date,
        data_rate: DataRate,
        rinex_version: RinexVersion,
        data_center: DataCenter
    ) -> List[Listing]:
        connection = self.connections_.get(data_center, None)
        if not connection:
            connection = Connection(
                data_center,
                self.username,
                self.password
            )
            self.connections_[data_center] = connection

        for path in data_center.directory(
            rinex_version=rinex_version,
            data_rate=data_rate,
            date=date,
            data_type=data_type,
            hour=hour
        ):
            if path in self.visited:
                continue
            self.visited.add(path)
            filenames = await connection.list(path)
            lst = []
            for filename in filenames:
                try:
                    file = GNSSDataFile(filename)
                    if (
                        file.rinex_version not in self.rinex_versions or
                        (
                            self.stations and
                            file.station.lower()[0:4]
                            not in self.stations
                        ) or file.data_type not in self.data_types
                    ):
                        continue
                except ValueError:
                    print(f'Unrecognized file: {filename}')
                    continue

                lst.append(
                    Listing(
                        protocol=data_center.protocol,
                        domain=data_center.domain,
                        port=data_center.port,
                        filename=file,
                        directory=path,
                        size=None,  # todo when available
                        data_center=data_center
                    )
                )
            return lst

    def __iter__(self) -> Generator[Listing, None, None]:
        self.visited = set()

        # data_centers should always be last in this product because this will
        # ensure that when there is more than one data center, requests to
        # separate data centers are made asynchronously before different
        # requests to the same data center
        search_list = product(
            self.hours,
            self.data_types,
            self.dates,
            self.data_rates,
            self.rinex_versions,
            self.data_centers
        )
        for chunk in chunks(search_list, self.async_queues):
            for lst in await asyncio.gather(
                *[
                    asyncio.create_task(self.read_dir(*search))
                    for search in chunk
                ]
            ):
                for item in lst:
                    yield item


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
