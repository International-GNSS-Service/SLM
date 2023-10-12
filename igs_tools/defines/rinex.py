from datetime import date
from enum_properties import (
    IntEnumProperties,
    IntFlagProperties,
    p,
    s,
    specialize
)


class RinexVersion(
    IntEnumProperties,
    s('label'), s('major'), s('slug'), p('published')
):
    """
    Todo change this to store minor versions in the msbs like DataRate
    """

    # Minor version not known

    #      Name    Label     Major Text           Published
    v1    = 1,   'RINEX 1',    1,  '1', date(year=1988, month=1, day=1)
    v2    = 2,   'RINEX 2',    2,  '2', date(year=1993, month=4, day=1)
    v3    = 3,   'RINEX 3',    3,  '3', date(year=2007, month=11, day=28)
    v4    = 4,   'RINEX 4',    4,  '4', date(year=2021, month=12, day=1)
    ###############################################################

    # todo
    # bits 0-11 are reserved for major versions

    # bits 12-15 are reserved for version 2 minor version

    # bits 16-20 are reserved for version 3 minor version

    # bits 21-25 are reserved for version 4 minor version

    # remaining bits > 25 are reserved for future version minor versions

    v2_11 = 211, 'RINEX 2.11', 2, '2.11', date(year=2012, month=6, day=26)
    v3_00 = 300, 'RINEX 3.00', 3, '3.00', date(year=2007, month=11, day=28)
    v3_01 = 301, 'RINEX 3.01', 3, '3.01', date(year=2009, month=6, day=22)
    v3_02 = 302, 'RINEX 3.02', 3, '3.02', date(year=2013, month=4, day=13)
    v3_03 = 303, 'RINEX 3.03', 3, '3.03', date(year=2017, month=1, day=25)
    v3_04 = 304, 'RINEX 3.04', 3, '3.04', date(year=2018, month=11, day=23)
    v3_05 = 305, 'RINEX 3.05', 3, '3.05', date(year=2020, month=12, day=1)
    v4_00 = 400, 'RINEX 4.00', 4, '4.00', date(year=2021, month=12, day=1)

    def major_q(self, field_name='rinex_version'):
        """
        # todo move this out of igs_tools
        :param field_name:
        :return:
        """
        from django.db.models import Q
        return Q(**{
            f'{field_name}__in': [
                rv.value for rv in RinexVersion if rv.major == self.major
            ]})

    @classmethod
    def major_versions(cls):
        return [cls.v2, cls.v3, cls.v4]

    # @property
    # def major(self):
    #     return RinexVersion(self._major)

    def __str__(self):
        return str(self.label)


try:
    from enum import KEEP
    init_data_rate = {
        'boundary': KEEP
    }
except ImportError:
    init_data_rate = {}


class DataRate(
    IntFlagProperties,
    s('label'),
    s('slug', case_fold=True),
    **init_data_rate
):
    """
    DataRate categorizes the data rate of a rinex file into DAILY, HOURLY, or
    HIGH_RATE files. This Enumeration can be used to track which files are
    present as well as the period in seconds of the data in each category
    of file rate. For instance, create a daily DataRate of 30 seconds:

    >>> DataRate.DAILY | DataRate.DAILY.period(30)

    Create a HighRate DataRate with a period of 1 second and a daily data rate
    with a period of 15 seconds:

    >>> DataRate.HIGH_RATE | DataRate.DAILY | DataRate.HIGH_RATE.period(1) | DataRate.DAILY.period(15)
    """

    DAILY     =  2**1, 'Daily',     'daily'
    HOURLY    =  2**2, 'Hourly',    'hourly'
    HIGH_RATE =  2**3, 'High Rate', 'high'

    # bits 4-16 are reserved for daily data rate in seconds

    # bits 17-27 are reserved for hourly data rate in seconds

    # bits 28-32 are reserved for high rate data rate in seconds

    def __str__(self):
        return str(', '.join(
            [f'{rt[0].label}: {rt[1]} seconds'
             if rt[1] is not None else
             rt[0].label
             for rt in self.periods]
        ))

    @property
    def periods(self):
        def get_period(rate):
            if rate == self.DAILY:
                return self.daily_period
            elif rate == self.HOURLY:
                return self.hourly_period
            elif rate == self.HIGH_RATE:
                return self.high_rate_period
            return None

        return [
            (rt, get_period(rt) or None) for rt in self
        ]

    @specialize(DAILY)
    def period(self, seconds):
        if seconds > 2**12:
            raise ValueError('Daily period must be less than 4096 seconds')
        return seconds << 4 & 0b00000000000000001111111111111000

    @specialize(HOURLY)
    def period(self, seconds):
        if seconds > 2**10:
            raise ValueError('Hourly period must be less than 1024 seconds')
        return seconds << 17 & 0b00000111111111110000000000000000

    @specialize(HIGH_RATE)
    def period(self, seconds):
        if seconds > 2**5:
            raise ValueError('High rate period must be less than 32 seconds')
        return seconds << 28 & 0b11111000000000000000000000000000

    @property
    def daily_period(self):
        return self.value >> 4 & 0b111111111111

    @property
    def hourly_period(self):
        return self.value >> 17 & 0b1111111111

    @property
    def high_rate_period(self):
        return self.value >> 28 & 0b11111
