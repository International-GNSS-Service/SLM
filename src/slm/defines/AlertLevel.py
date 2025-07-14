from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s


class AlertLevel(IntegerChoices):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    NOTICE  = 1, _("NOTICE")
    WARNING = 2, _("WARNING")
    ERROR   = 3, _("ERROR")
    # fmt: on

    def __str__(self):
        return str(self.label)

    @property
    def css(self):
        """
        The clss class to use for this level.
        """
        return f"slm-alert-{self.name.lower()}"

    @property
    def color(self):
        """
        The hex code of the color to use for this level.
        """
        from django.conf import settings

        return getattr(settings, "SLM_ALERT_COLORS", {}).get(self, None)
