from enum import nonmember

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, p, s


class AntennaFeatures(IntEnumProperties, p("label")):
    _symmetric_builtins_ = [s("name", case_fold=True)]
    do_not_call_in_templates = nonmember(True)

    # fmt: off
    MMI = 1,  _("(MMI) Man-Machine Interface")
    NOM = 2,  _("(NOM) North Orientation Mark")
    RXC = 3,  _("(RXC) Receiver Connector")
    BAT = 4,  _("(BAT) Battery Compartment Door Release")
    BTD = 5,  _("(BTD) Bottom of Tear Drop Shape")
    CMP = 6,  _("(CMP) Mounted Compass")
    DIS = 7,  _("(DIS) Display/Digital Readout")
    DRY = 8,  _("(DRY) Cap or Cover for Drying Agent")
    PCS = 9,  _("(PCS) PC Card Slot")
    TMT = 10, _("(TMT) Tape Measure Tab or Notch for Slant Height Pole")
    CAC = 11, _("(CAC) Nonspecific Cable Connector")
    CTC = 12, _("(CTC) External Controller Connector")
    DAC = 13, _("(DAC) Data Cable Connector")
    PWC = 14, _("(PWC) Power Port")
    RTC = 15, _("(RTC) RTK Connector")
    UNK = 16, _("(UNK) Unknown")
    OMM = 17, _("(OMM) Opposite of Man-Machine Interface")
    # fmt: on

    def __str__(self):
        return self.name
