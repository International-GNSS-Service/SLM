from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class AntennaReferencePoint(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    BAM = 1, _('Bottom of Antenna Mount')
    BCR = 2, _('Bottom of Chokering')
    BDG = 3, _('Bottom of Dome Ground Plane')
    BGP = 4, _('Bottom of Ground Plane')
    BPA = 5, _('Bottom of Preamplifier')
    TCR = 6, _('Top of Chokering')
    TDG = 7, _('Top of Dome Ground Plane')
    TGP = 8, _('Top of Ground Plane')
    TOP = 9, _('Top of Pole')
    TPA = 10, _('Top of Preamplifier')

    def __str__(self):
        return self.name
