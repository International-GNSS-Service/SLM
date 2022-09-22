from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class SatelliteSystem(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    GPS   = 1, _('GPS')
    GLO   = 2, _('GLONASS')
    GAL   = 3, _('GALILEO')
    BDS   = 4, _('Beidou')
    QZSS  = 5, _('QZSS')
    SBAS  = 6, _('SBAS')
    IRNSS = 7, _('IRNSS')
