from enum import nonmember
from typing import Annotated

from django.utils.translation import gettext_lazy as _
from enum_properties import StrEnumProperties, Symmetric


class CardinalDirection(StrEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: str

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
