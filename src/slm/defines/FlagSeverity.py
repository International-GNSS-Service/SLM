from enum import nonmember

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, p, s


class FlagSeverity(IntEnumProperties, p("label")):
    _symmetric_builtins_ = [s("name", case_fold=True)]
    do_not_call_in_templates = nonmember(True)

    # fmt: off
    BLOCK_SAVE    = 1, _("Block Save")
    BLOCK_PUBLISH = 2, _("Block Publish")
    NOTIFY        = 3, _("Notify")
    # fmt: on

    def __str__(self):
        return str(self.label)
