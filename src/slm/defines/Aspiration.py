from enum import nonmember
from typing import Annotated

from enum_properties import StrEnumProperties, Symmetric


class Aspiration(StrEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: Annotated[str, Symmetric(case_fold=True)]

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    UNASPIRATED = "U", "UNASPIRATED"
    NATURAL     = "N", "NATURAL"
    FAN         = "F", "FAN"
    # fmt: on

    def __str__(self):
        return str(self.label)
