from django.utils.translation import gettext_lazy as _
from django_enum import TextChoices
from enum_properties import s


class CardinalDirection(TextChoices):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    NORTH = "N", _("North")
    SOUTH = "S", _("South")
    EAST = "E", _("East")
    WEST = "W", _("West")
    NORTH_WEST = "NW", _("North West")
    NORTH_EAST = "NE", _("North East")
    SOUTH_WEST = "SW", _("South West")
    SOUTH_EAST = "SE", _("South East")

    def __str__(self):
        return str(self.label)
