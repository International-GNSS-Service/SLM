from enum import nonmember
from typing import Annotated

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, Symmetric


class AlertLevel(IntEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: str

    do_not_call_in_templates = nonmember(True)

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
