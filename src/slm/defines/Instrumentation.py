from enum import nonmember

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, p, s


class Instrumentation(IntEnumProperties, p("label")):
    _symmetric_builtins_ = [s("name", case_fold=True)]
    do_not_call_in_templates = nonmember(True)

    # fmt: off
    GPS     = 1, _("GPS")
    GLONASS = 2, _("GLONASS")
    DORIS   = 3, _("DORIS")
    PRARE   = 4, _("PRARE")
    SLR     = 5, _("SLR")
    VLBI    = 6, _("VLBI")
    TIME    = 7, _("TIME")
    ETC     = 8, _("etc")
    # fmt: on

    def __str__(self):
        return str(self.label)
