from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import p, s


class EquipmentState(IntegerChoices, p("help_text")):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    ACTIVE = 100, _("Active"), _("This equipment is in active use.")
    LEGACY = (
        101,
        _("Legacy"),
        _("This equipment is not in active use or its coding has changed."),
    )
    UNVERIFIED = (
        102,
        _("Unverified"),
        _("This equipment information has not been vetted."),
    )

    def __str__(self):
        return str(self.label)
