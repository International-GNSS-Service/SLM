from enum import nonmember

from django.utils.translation import gettext_lazy as _
from enum_properties import StrEnumProperties, p, s


class CardinalDirection(StrEnumProperties, p("label")):
    _symmetric_builtins_ = [s("name", case_fold=True)]
    do_not_call_in_templates = nonmember(True)

    # fmt: off
    NORTH      =  "N", _("North")
    SOUTH      =  "S", _("South")
    EAST       =  "E", _("East")
    WEST       =  "W", _("West")
    NORTH_WEST = "NW", _("North West")
    NORTH_EAST = "NE", _("North East")
    SOUTH_WEST = "SW", _("South West")
    SOUTH_EAST = "SE", _("South East")
    # fmt: on

    def __str__(self):
        return str(self.label)
