from django_enum import TextChoices
from enum_properties import s


class FrequencyStandardType(TextChoices, s("geodesy_ml", case_fold=True)):
    _symmetric_builtins_ = [s("name", case_fold=True), s("label", case_fold=True)]

    # fmt: off
    INTERNAL          = "I", "INTERNAL",          "INTERNAL"
    EXTERNAL_H_MASER  = "H", "EXTERNAL H-MASER",  "H-MASER"
    EXTERNAL_CESIUM   = "C", "EXTERNAL CESIUM",   "CESIUM"
    EXTERNAL_RUBIDIUM = "R", "EXTERNAL RUBIDIUM", "RUBIDIUM"
    EXTERNAL_QUARTZ   = "Q", "EXTERNAL QUARTZ",   "QUARTZ"
    # fmt: on

    def __str__(self):
        return str(self.label)
