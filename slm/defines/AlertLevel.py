from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s, p


class AlertLevel(IntegerChoices, p('bootstrap')):

    _symmetric_builtins_ = [s('name', case_fold=True)]

    NOTICE  = 0, _('NOTICE'),  'info'
    WARNING = 1, _('WARNING'), 'warning'
    ERROR   = 2, _('ERROR'),   'danger'

    def __str__(self):
        return str(self.label)

    @property
    def color(self):
        from django.conf import settings
        return getattr(settings, 'SLM_ALERT_COLORS', {}).get(self, None)
