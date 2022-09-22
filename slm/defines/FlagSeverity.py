from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class FlagSeverity(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    BLOCK_SAVE =    0, _('Block Save')
    BLOCK_PUBLISH = 1, _('Block Publish')
    NOTIFY =        2, _('Notify')
