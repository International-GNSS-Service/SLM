from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s


class AlertLevel(IntegerChoices, s('bootstrap', case_fold=True)):

    _symmetric_builtins_ = [s('name', case_fold=True)]

    INFO    = 0, _('INFO'), 'info'
    WARNING = 1, _('WARNING'), 'warning'
    ERROR   = 2, _('ERROR'), 'danger'

    def __str__(self):
        return str(self.label)
