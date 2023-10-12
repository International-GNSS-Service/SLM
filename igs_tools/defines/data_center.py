from enum_properties import EnumProperties, IntFlagProperties, p, s, specialize
from pathlib import Path
from .rinex import DataRate, RinexVersion
from .data_type import DataType
from igs_tools.utils import day_of_year, classproperty
from copy import copy
from functools import reduce
from itertools import product
from datetime import date as Date
from typing import Optional


class DataCenterCategory(EnumProperties, s('label'), p('link')):
    """
    IGS has three categories of data centers.

    https://igs.org/data-access/#definitions
    """

    GLOBAL      = 'G', 'Global',      'https://igs.org/data-access/#global-dcs'
    REGIONAL    = 'R', 'Regional',    'https://igs.org/data-access/#regional-dcs'
    OPERATIONAL = 'O', 'Operational', 'https://igs.org/data-access/#operational-project-dcs'


class DataCenter(
    IntFlagProperties,
    p('data'), p('gnss_root'), p('category'), s('full_name'), s('url'), p('info')
):
    """
    The Data Centers offering open access online archives of GNSS data. This
    includes all of the global and regional data centers and a subset of the
    operational data centers.
    """

    # name  value           data                    gnss_root                  category                           full_name                                                url                                       info
    # *- Global Data Centers -*
    CDDIS = 2**0,  'https://cddis.nasa.gov', Path('/archive/gnss/data'), DataCenterCategory.GLOBAL, 'NASA Center for Data and Information Services',                 'https://cddis.nasa.gov',     'https://cddis.gsfc.nasa.gov/Data_and_Derived_Products/GNSS/GNSS_data_and_product_archive.html'
    ESA   = 2**1,  'ftp://gssc.esa.int',     Path('/cddis/gnss/data'),   DataCenterCategory.GLOBAL, 'European Space Agency',                                         'https://gssc.esa.int',       'http://navigation-office.esa.int/GNSS_based_products.html'
    IGN   = 2**2,  'ftp://igs.ign.fr',       Path('/pub/igs/data'),      DataCenterCategory.GLOBAL, "Institut National de l'Information Géographique et Forestière", 'https://www.ign.fr',         'https://www.ign.fr'
    KASI  = 2**3,  'ftp://nfs.kasi.re.kr',   Path('/gps/data'),          DataCenterCategory.GLOBAL, 'Korea Astronomy and Space Science Institute',                   'https://gnss.kasi.re.kr',    'https://gnss.kasi.re.kr/gdc_download.php'
    SIO   = 2**4,  'ftp://garner.ucsd.edu',  Path('/pub/rinex'),         DataCenterCategory.GLOBAL, 'Scripps Institution of Oceanography',                           'http://sopac-csrc.ucsd.edu', 'http://sopac-csrc.ucsd.edu/index.php/data-download'
    WHU   = 2**5,  'ftp://igs.gnsswhu.cn',   Path('/pub/gps/data'),      DataCenterCategory.GLOBAL, 'Wuhan University',                                              'https://en.whu.edu.cn',      'http://www.igs.gnsswhu.cn/index.php/home/index/index.html'

    # *- Regional Data Centers -*



    # *- Operational Project Data Centers -*


    @classproperty
    def global_centers(cls):
        return reduce(lambda x, y: x | y, [
            center for center in cls
            if center.category is DataCenterCategory.GLOBAL
        ], DataCenter(0))

    @classproperty
    def regional_centers(cls):
        return reduce(lambda x, y: x | y, [
            center for center in cls
            if center.category is DataCenterCategory.REGIONAL
        ], DataCenter(0))

    @classproperty
    def operational_centers(cls):
        return reduce(lambda x, y: x | y, [
            center for center in cls
            if center.category is DataCenterCategory.OPERATIONAL
        ], DataCenter(0))

    @property
    def protocol(self):
        return self.data.split(':')[0]

    @property
    def label(self):
        return self.name

    def __str__(self):
        return str(self.name)

    def directory(
            self,
            rinex_version: RinexVersion,
            data_rate: DataRate,
            date: Date,
            data_type: DataType,
            hour: Optional[int] = None
    ):
        """
        Return a list of paths for the given data parameters. A single date
        may have multiple paths, for example, if the data is split into hourly
        files. If the data center has no data matching the criteria an empty
        list is returned.

        :param rinex_version: The rinex version of the data.
        :param data_rate: The rate of the data.
        :param date: The day to fetch data for.
        :param data_type: The type of data to fetch.
        :param hour: The hour to fetch data for. If None the first hour is
            fetched if the directory contains an hour parameter.
        :return: A list of paths to the data.
        """
        raise NotImplementedError(f'{self} must implement directory()')

    def directories(
        self, rinex_versions, data_rates, dates, data_types, hours
    ):
        return [
            self.directory(*args)
            for args in product(
                rinex_versions, data_rates, dates, data_types, hours
            )
        ]

    @specialize(CDDIS)
    def directory(
        self, rinex_version, data_rate, date, data_type, hour=None
    ):
        path = copy(self.path)
        if data_rate in [DataRate.HOURLY, DataRate.HIGH_RATE]:
            path /= 'hourly'
        elif data_rate == DataRate.DAILY:
            path /= 'daily'
        path /= str(date.year)
        path /= f'{day_of_year(date):03d}'
        if data_rate in [DataRate.DAILY, DataRate.HIGH_RATE]:
            path /= f'{str(date.year)[2:]}{r2code}'
        elif data_rate is DataRate.HOURLY:
            path /= f'{hour or 1:0>2d}'
        return path

    @specialize(IGN)
    def directory(
        self, rinex_version, data_rate, date, data_type, hour=None
    ):
        path = copy(self.path)
        if data_rate == DataRate.HOURLY:
            path /= 'hourly'
        elif data_rate == DataRate.HIGH_RATE:
            path /= 'highrate'
        path /= str(date.year)
        path /= f'{day_of_year(date):03d}'
        return [str(path)]

    @specialize(KASI)
    def directory(
        self, rinex_version, data_rate, date, data_type, hour=None
    ):
        path = copy(self.path)
        if data_rate == DataRate.HOURLY or data_rate == DataRate.HIGH_RATE:
            return None
        elif data_rate == DataRate.DAILY:
            path /= 'daily'
        path /= str(date.year)
        path /= f'{day_of_year(date):03d}'
        path /= f'{str(date.year)[2:]}d'
        return [str(path)]

    @specialize(SIO)
    def directory(
        self, rinex_version, data_rate, date, data_type, hour=None
    ):
        path = copy(self.path)
        if data_rate == DataRate.HOURLY:
            return None
        elif data_rate == DataRate.HIGH_RATE:
            path /= 'rinex_highrate'
        path /= str(date.year)
        path /= f'{day_of_year(date):03d}'
        return [str(path)]

    @specialize(WHU)
    def directory(
        self, rinex_version, data_rate, date, data_type, hour=None
    ):
        path = copy(self.path)
        if data_rate == DataRate.DAILY:
            path /= 'daily'
        if data_rate == DataRate.HOURLY:
            return None
        elif data_rate == DataRate.HIGH_RATE:
            return []
        path /= str(date.year)
        path /= f'{day_of_year(date):03d}'
        return [str(path)]
