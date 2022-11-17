from django_enum import TextChoices
from enum_properties import s


class CollocationStatus(TextChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    PERMANENT = 'P', 'PERMANENT'
    HOURLY    = 'M', 'MOBILE'
