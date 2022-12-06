from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class AlertLevel(IntegerChoices, s('bootstrap', case_fold=True)):

    _symmetric_builtins_ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    INFO    = 0, _('INFO'), 'info'
    WARNING = 1, _('WARNING'), 'warning'
    ERROR   = 2, _('ERROR'), 'danger'
