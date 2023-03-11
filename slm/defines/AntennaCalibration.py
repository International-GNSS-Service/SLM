from django_enum import IntegerChoices
from enum_properties import s


class AntennaCalibration(IntegerChoices):

    _symmetric_builtins_ = [s('name', case_fold=True)]

    CONVERTED = 0, 'CONVERTED'
    #ONE = 1, 'ONE', todo real?
    #TWO = 2, 'TWO'
    ROBOT = 1, 'ROBOT'
    FIELD = 2, 'FIELD'
    CHAMBER = 3, 'CHAMBER'
    #FOUR = 4, 'FOUR'
    ESA = 5, 'ESA'
    #SIX = 6, 'SIX'
    JAXA = 7, 'JAXA'
    ISRO = 8, 'ISRO'
    CSNO_TARC = 9, 'CSNO/TARC'

    def __str__(self):
        return str(self.label)
