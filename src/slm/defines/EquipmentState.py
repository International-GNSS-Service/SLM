from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import p, s


class EquipmentState(IntegerChoices, p("help_text")):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    ACTIVE     = 100, _("In Use"),     _("This coding is in active use.")
    LEGACY     = 101, _("Retired"),    _("This equipment coding has changed.")
    UNVERIFIED = 102, _("Unverified"), _("This equipment coding has not been verified.")
    # fmt: on

    def __str__(self):
        return str(self.label)
