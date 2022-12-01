from django_enum import TextChoices
from enum_properties import s


class Aspiration(TextChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    UNASPIRATED = 'U',  'UNASPIRATED'
    NATURAL     = 'N',  'NATURAL'
    FAN         = 'F',  'FAN'
