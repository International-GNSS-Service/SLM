from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _
from django.conf import settings


class SiteLogStatus(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    DORMANT     = 0, _('Dormant')
    PENDING     = 1, _('Pending')
    UPDATED     = 2, _('Updated')
    PUBLISHED   = 3, _('Published')

    @property
    def css(self):
        return f'slm-status-{self.label.lower()}'
    
    @property
    def color(self):
        return getattr(settings, 'SLM_STATUS_COLORS', {}).get(self, None)

    @property
    def color(self):
        return getattr(settings, 'SLM_STATUS_COLORS', {}).get(self, None)

    def merge(self, other):
        if other.value < self.value:
            return other
        return self
