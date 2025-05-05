from django_enum import IntegerChoices
from enum_properties import s


class AntennaCalibrationMethod(IntegerChoices):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    CONVERTED = 0, "CONVERTED"
    ROBOT     = 1, "ROBOT"
    FIELD     = 2, "FIELD"
    CHAMBER   = 3, "CHAMBER"
    COPIED    = 4, "COPIED"
    # fmt: on

    #  todo real?
    # ONE = 1, 'ONE',
    # TWO = 2, 'TWO'
    # FOUR = 4, 'FOUR'
    # ESA = 5, 'ESA'
    # SIX = 6, 'SIX'
    # JAXA = 7, 'JAXA'
    # ISRO = 8, 'ISRO'
    # CSNO_TARC = 9, 'CSNO/TARC'

    def __str__(self):
        return str(self.label)
