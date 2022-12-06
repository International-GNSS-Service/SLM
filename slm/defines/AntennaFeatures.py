from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class AntennaFeatures(IntegerChoices):

    _symmetric_builtins_ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    MMI = 1, _("Man-Machine Interface")
    NOM = 2, _("North Orientation Mark")
    RXC = 3, _("Receiver Connector")
    BAT = 4, _("Battery Compartment Door Release")
    BTD = 5, _("Bottom of Tear Drop Shape")
    CMP = 6, _("Mounted Compass")
    DIS = 7, _("Display/Digital Readout")
    DRY = 8, _("Cap or Cover for Drying Agent")
    PCS = 9, _("PC Card Slot")
    TMT = 10, _("Tape Measure Tab or Notch for Slant Height Pole")
    CAC = 11, _("Nonspecific Cable Connector")
    CTC = 12, _("External Controller Connector")
    DAC = 13, _("Data Cable Connector")
    PWC = 14, _("Power Port")
    RTC = 15, _("RTK Connector")
    UNK = 16, _("Unknown")
