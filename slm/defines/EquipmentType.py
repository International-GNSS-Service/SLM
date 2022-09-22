from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class EquipmentType(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    RECEIVER = 100, _('Receiver')
    ANTENNA  = 101, _('Antenna')
    DOME     = 102, _('Dome')
