from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class Instrumentation(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    GPS     = 1, _('GPS')
    GLONASS = 2, _('GLONASS')
    DORIS   = 3, _('DORIS')
    PRARE   = 4, _('PRARE')
    SLR     = 5, _('SLR')
    VLBI    = 6, _('VLBI')
    TIME    = 7, _('TIME')
    ETC     = 8, _('etc')
