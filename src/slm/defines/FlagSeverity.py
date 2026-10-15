from enum import nonmember
from typing import Annotated

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, Symmetric


class FlagSeverity(IntEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: str

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    BLOCK_SAVE    = 1, _("Block Save")
    BLOCK_PUBLISH = 2, _("Block Publish")
    NOTIFY        = 3, _("Notify")
    # fmt: on

    def __str__(self):
        return str(self.label)
