from enum import nonmember
from typing import Annotated

from enum_properties import StrEnumProperties, Symmetric


class FrequencyStandardType(StrEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: Annotated[str, Symmetric(case_fold=True)]
    geodesy_ml: Annotated[str, Symmetric(case_fold=True)]

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    INTERNAL          = "I", "INTERNAL",          "INTERNAL"
    EXTERNAL_H_MASER  = "H", "EXTERNAL H-MASER",  "H-MASER"
    EXTERNAL_CESIUM   = "C", "EXTERNAL CESIUM",   "CESIUM"
    EXTERNAL_RUBIDIUM = "R", "EXTERNAL RUBIDIUM", "RUBIDIUM"
    EXTERNAL_QUARTZ   = "Q", "EXTERNAL QUARTZ",   "QUARTZ"
    # fmt: on

    def __str__(self):
        return str(self.label)
