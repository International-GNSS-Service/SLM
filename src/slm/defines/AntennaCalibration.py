from enum import nonmember
from typing import Annotated

from enum_properties import IntEnumProperties, Symmetric


class AntennaCalibrationMethod(IntEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: str

    do_not_call_in_templates = nonmember(True)

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
