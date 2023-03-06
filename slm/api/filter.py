from django.http import QueryDict
from django_filters import (
    BaseInFilter,
    NumberFilter,
    DateTimeFilter,
    FilterSet
)
from django_filters import compat
from django_filters.filterset import BaseFilterSet
from django.forms import DateTimeField
from django.forms.utils import from_current_timezone
from django.core.exceptions import ValidationError
from dateutil import parser
from django.utils.translation import gettext as _
from django_filters import BooleanFilter
from slm.forms import SLMBooleanField


class SLMBooleanFilter(BooleanFilter):
    field_class = SLMBooleanField


class CrispyFormCompat:
    """
    Ensure the given form as a submit button and correct method set!
    """

    @property
    def form(self):
        form = BaseFilterSet.form.fget(self)

        if compat.is_crispy():
            from crispy_forms.helper import FormHelper
            from crispy_forms.layout import Layout, Submit

            helper = getattr(form, 'helper', None)
            if helper:
                # add on a submit button if one does not exist on the form
                def has_submit(fields):
                    for field in fields:
                        if (
                            isinstance(field, Submit) or
                            has_submit(getattr(field, 'fields', []))
                        ):
                            return True
                    return False

                if not has_submit(form.helper.layout.fields):
                    helper.layout = Layout(
                        *helper.layout.fields,
                        Submit('', _('Submit'), css_class='btn btn-primary')
                    )
            else:
                form.helper = FormHelper()
                form.helper.form_method = 'GET'
                form.helper.layout = Layout(
                    *form.fields.keys(),
                    Submit('', _('Submit'), css_class='btn btn-primary')
                )
        return form


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
                    stripped.setlist(key, data.getlist(key))
                    if len(stripped[key]) == 1:
                        stripped[key] = stripped[key][0]
            data = stripped
        super().__init__(data=data, *args, **kwargs)


class MustIncludeThese(BaseInFilter, NumberFilter):

    def __init__(self, field_name='pk', *args, **kwargs):
        super().__init__(field_name=field_name, *args, **kwargs)

    def filter(self, qs, value):
        if value:
            qs |= super().filter(qs.model.objects.all(), value).distinct()
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
