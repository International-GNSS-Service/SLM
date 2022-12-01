from django_enum import TextChoices
from enum_properties import s


class FrequencyStandardType(TextChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    INTERNAL          = 'I',  'INTERNAL'
    EXTERNAL_H_MASER  = 'H',  'EXTERNAL H-MASER'
    EXTERNAL_CESIUM   = 'C',  'EXTERNAL CESIUM'
    EXTERNAL_RUBIDIUM = 'R',  'EXTERNAL RUBIDIUM'
