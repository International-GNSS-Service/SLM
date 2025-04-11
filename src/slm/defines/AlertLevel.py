from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s


class AlertLevel(IntegerChoices):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    NOTICE = 1, _("NOTICE")
    WARNING = 2, _("WARNING")
    ERROR = 3, _("ERROR")

    def __str__(self):
        return str(self.label)

    @property
    def css(self):
        return f"slm-alert-{self.name.lower()}"

    @property
    def color(self):
        from django.conf import settings

        return getattr(settings, "SLM_ALERT_COLORS", {}).get(self, None)
