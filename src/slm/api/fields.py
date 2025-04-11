from datetime import date, datetime, time, timezone

from dateutil import parser
from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils.translation import gettext as _
from rest_framework.serializers import DateTimeField, Field


class SLMDateTimeField(DateTimeField):
    default_error_messages = {
        "invalid": _("Unable to interpret datetime, please use format: {format}."),
        "parse": _("Please use format: {format}: {error}"),
    }

    """
    A much more lenient datetime field that uses dateutil to parse. This field
    differs from the vanilla DRF DateTimeField in several ways:
    
    1) dateutil.parser is used to parse incoming strings. This is very lenient.
    2) Values that are just dates default to default_time if it is set, and
        fail otherwise.
    3) The timezone is set to UTC unless otherwise given.
    
    :param default_time: Use this time for incoming values that are just dates.
        defaults to midnight.
    :param default_timezone: This is the output timezone - defaults to UTC.
    :param kwargs: kwargs for DRF base classes.
    """

    default_time = time(hour=0, minute=0, second=0)

    def __init__(
        self, default_time=default_time, default_timezone=timezone.utc, **kwargs
    ):
        self.default_time = default_time
        super().__init__(default_timezone=default_timezone, **kwargs)

    def default_timezone(self):
        return timezone.utc if settings.USE_TZ else None

    def to_internal_value(self, value):
        if isinstance(value, date) and not isinstance(value, datetime):
            # assume midnight
            if not self.default_time:
                self.fail("date")
            value = datetime.combine(value, self.default_time)

        if isinstance(value, datetime):
            return self.enforce_timezone(value)

        try:
            parsed = parser.parse(value)
            if parsed is not None:
                return self.enforce_timezone(parsed)
        except parser.ParserError as pe:
            self.fail("parse", format="CCYY-MM-DDThh:mmZ", error=str(pe))
        except (ValueError, TypeError):
            pass

        self.fail("invalid", format="CCYY-MM-DDThh:mmZ")


class SLMPointField(Field):
    default_error_messages = {
        "invalid": _(
            "Unable to interpret point ({data}), please use format: {format}."
        ),
        "missing": _("Must provide all {num} values, received: {received}."),
    }

    def to_representation(self, value):
        return value.coords

    def to_internal_value(self, data):
        try:
            coords = [None if coord in ["", None] else float(coord) for coord in data]
            # all values must be null or a number
            if any([coord is None for coord in coords]) and not all(
                [coord is None for coord in coords]
            ):
                self.fail(
                    "missing",
                    num=len(coords),
                    received=len([coord for coord in coords if coord is not None]),
                )
            return Point(*coords) or None
        except (TypeError, ValueError):
            self.fail("invalid", format="[float, float, float]", data=data)
