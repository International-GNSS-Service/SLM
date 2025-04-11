from enum_properties import EnumProperties, p, s
from pathlib import Path
from .rinex import DataRate
from igs_tools.utils import day_of_year


class DataCenter(
    EnumProperties,
    p('protocol'), s('domain'), p('port'), s('full_name')
):

    IGN   = 'IGN',   'ftp',   'igs.ign.fr',             21,  "Institut National de l'Information Géographique et Forestière"
    SIO   = 'SIO',   'ftp',   'garner.ucsd.edu',        21,  'Scripps Institution of Oceanography'
    KASI  = 'KASI',  'ftp',   'nfs.kasi.re.kr',         21,  'Korea Astronomy and Space Science Institute'
    CDDIS = 'CDDIS', 'https', 'https://cddis.nasa.gov', 443, 'NASA Center for Data and Information Services'

    @property
    def label(self):
        return self.name

    def __str__(self):
        return str(self.label)

    def directory(self, rinex_version, data_rate, date, hours=None):
        """
        todo this interface should be changed to return a list of paths and
        honor the hours parameter
        :param rinex_version:
        :param data_rate:
        :param date:
        :param hours:
        :return:
        """
        if self == self.IGN:
            path = Path('/pub/igs/data')
            if data_rate == DataRate.HOURLY:
                path /= 'hourly'
            elif data_rate == DataRate.HIGH_RATE:
                path /= 'highrate'
            path /= str(date.year)
            path /= f'{day_of_year(date):03d}'
            return str(path)
        if self == self.SIO:
            path = Path('/pub/rinex')
            if data_rate == DataRate.HOURLY:
                return None
            elif data_rate == DataRate.HIGH_RATE:
                path /= 'rinex_highrate'
            path /= str(date.year)
            path /= f'{day_of_year(date):03d}'
            return str(path)
        if self == self.KASI:
            path = Path('/gps/data')  # todo add constellation to list
            if data_rate == DataRate.HOURLY or data_rate == DataRate.HIGH_RATE:
                return None
            elif data_rate == DataRate.DAILY:
                path /= 'daily'
            path /= str(date.year)
            path /= f'{day_of_year(date):03d}'
            path /= f'{str(date.year)[2:]}d'
            return str(path)
        if self == self.CDDIS:
            path = Path('/archive/gnss/data')
            if data_rate in [DataRate.HOURLY, DataRate.HIGH_RATE]:
                path /= 'hourly'
            elif data_rate == DataRate.DAILY:
                path /= 'daily'
            path /= str(date.year)
            path /= f'{day_of_year(date):03d}'
            if data_rate in [DataRate.DAILY, DataRate.HIGH_RATE]:
                path /= f'{str(date.year)[2:]}d'
            if data_rate in [DataRate.HOURLY, DataRate.HIGH_RATE]:
                path /= '01'
            return path
        raise NotImplementedError(f'{self} must implement directory()')
