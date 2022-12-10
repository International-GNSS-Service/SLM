from django.utils.translation import gettext as _
from django_enum import IntegerChoices
from enum_properties import s


class EquipmentState(IntegerChoices):

    _symmetric_builtins_ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    ACTIVE = 100, _('Active')
    LEGACY = 101, _('Legacy')

    def __str__(self):
        return self.label
