from enum import nonmember

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, p, s


class EquipmentState(IntEnumProperties, p("label"), p("help_text")):
    _symmetric_builtins_ = [s("name", case_fold=True)]
    do_not_call_in_templates = nonmember(True)

    # fmt: off
    ACTIVE     = 100, _("In Use"),     _("This coding is in active use.")
    LEGACY     = 101, _("Retired"),    _("This equipment coding has changed.")
    UNVERIFIED = 102, _("Unverified"), _("This equipment coding has not been verified.")
    # fmt: on

    def __str__(self):
        return str(self.label)
