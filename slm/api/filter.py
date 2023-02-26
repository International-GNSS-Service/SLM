from django.http import QueryDict
from django_filters import (
    BaseInFilter,
    NumberFilter,
    DateTimeFilter,
    FilterSet
)
from django.forms import DateTimeField
from django.forms.utils import from_current_timezone
from django.core.exceptions import ValidationError
from dateutil import parser
from django.utils.translation import gettext as _
from django_filters import BooleanFilter
from slm.forms import SLMBooleanField


class SLMBooleanFilter(BooleanFilter):
    field_class = SLMBooleanField


class AcceptListArguments:
    """
    Automatic conversion of lists to GET parameters in AJAX seems to add pesky
    [] to the end of list arguments - there doesn't seem to be an easy way
    to handle this in FilterSets so we strip the brackets out with this mixin.

    It seems really really stupid that this is necessary...
    """

    def __init__(self, data=None, *args, **kwargs):
        if data:
            stripped = QueryDict(mutable=True)
            for key in data.keys():
                if key.endswith('[]'):
                    stripped.setlist(key[0:-2], data.getlist(key))
                else:
                    stripped[key] = data.get(key)
            data = stripped
        super().__init__(data=data, *args, **kwargs)


class MustIncludeThese(BaseInFilter, NumberFilter):

    def __init__(self, field_name='pk', *args, **kwargs):
        super().__init__(field_name=field_name, *args, **kwargs)

    def filter(self, qs, value):
        if value:
            qs |= super().filter(qs.model.objects.all(), value)
        return qs


class SLMDateTimeField(DateTimeField):
    """
    A DateTimeField that uses dateutil to parse datetimes. Much more lenient
    than the default parsers.
    """
    def to_python(self, value):
        try:
            return super().to_python(value)
        except ValidationError:
            try:
                return from_current_timezone(parser.parse(value))
            except parser.ParserError as pe:
                raise ValidationError(
                    _("Invalid date/time: {error}").format(str(pe)),
                    code="invalid"
                )


class SLMDateTimeFilter(DateTimeFilter):

    field_class = SLMDateTimeField


class InitialValueFilterSet(FilterSet):
    """
    This allows you to specify initial values that can also be callables on
    your field filters.
    """

    def __init__(self, data=None, *args, **kwargs):
        # if filterset is bound, use initial values as defaults
        if data is not None:
            # get a mutable copy of the QueryDict
            data = data.copy()
            for name, f in self.base_filters.items():
                initial = f.extra.get('initial')
                # filter param is either missing or empty, use initial as
                # default
                if not data.get(name) and initial:
                    data[name] = initial() if callable(initial) else initial

        super().__init__(data, *args, **kwargs)
