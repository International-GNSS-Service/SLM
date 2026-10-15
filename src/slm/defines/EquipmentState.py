from enum import nonmember
from typing import Annotated

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, Symmetric


class EquipmentState(IntEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: str
    help_text: str

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    ACTIVE     = 100, _("In Use"),     _("This coding is in active use.")
    LEGACY     = 101, _("Retired"),    _("This equipment coding has changed.")
    UNVERIFIED = 102, _("Unverified"), _("This equipment coding has not been verified.")
    # fmt: on

    def __str__(self):
        return str(self.label)
