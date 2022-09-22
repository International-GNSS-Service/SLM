from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class EquipmentState(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    ACTIVE = 100, _('Active')
    LEGACY = 101, _('Legacy')
