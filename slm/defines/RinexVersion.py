from django_enum import IntegerChoices
from enum_properties import s, p
from datetime import date


class RinexVersion(IntegerChoices, s('major'), p('published')):

    # Minor version not known
    v2    = 2,   'RINEX 2',    2, date(year=1993, month=4, day=1)
    v3    = 3,   'RINEX 3',    3, date(year=2007, month=11, day=28)
    v4    = 4,   'RINEX 4',    4, date(year=2021, month=12, day=1)
    ###############################################################

    v2_11 = 211, 'RINEX 2.11', 2, date(year=2012, month=6, day=26)
    v3_00 = 300, 'RINEX 3.00', 3, date(year=2007, month=11, day=28)
    v3_01 = 301, 'RINEX 3.01', 3, date(year=2009, month=6, day=22)
    v3_02 = 302, 'RINEX 3.02', 3, date(year=2013, month=4, day=13)
    v3_03 = 303, 'RINEX 3.03', 3, date(year=2017, month=1, day=25)
    v3_04 = 304, 'RINEX 3.04', 3, date(year=2018, month=11, day=23)
    v3_05 = 305, 'RINEX 3.05', 3, date(year=2020, month=12, day=1)
    v4_00 = 400, 'RINEX 4.00', 4, date(year=2021, month=12, day=1)
