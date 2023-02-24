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
from django.utils.functional import cached_property
from slm.models import (
    Site,
    Agency,
    Network,
    Alert
)
from django.db.models import Q
from django_enum.filters import EnumFilter
from slm.defines import SiteLogStatus, AlertLevel
import django_filters


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


class StationFilter(AcceptListArguments, FilterSet):

    @cached_property
    def alert_fields(self):
        """
        Fetch the mapping of alert names to related fields.
        """
        def get_related_field(alert):
            for obj in Site._meta.related_objects:
                if obj.related_model is alert:
                    return obj.name
        return {
            alert.__name__.lower(): get_related_field(alert)
            for alert in Alert.objects.site_alerts()
        }

    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )
    published_before = django_filters.CharFilter(
        field_name='last_publish',
        lookup_expr='lt'
    )
    published_after = django_filters.CharFilter(
        field_name='last_publish',
        lookup_expr='gte'
    )
    updated_before = django_filters.CharFilter(
        field_name='last_update',
        lookup_expr='lt'
    )
    updated_after = django_filters.CharFilter(
        field_name='last_update',
        lookup_expr='gte'
    )
    agency = django_filters.ModelMultipleChoiceFilter(
        field_name='agencies',
        queryset=Agency.objects.all(),
        distinct=True
    )
    network = django_filters.ModelMultipleChoiceFilter(
        field_name='networks',
        queryset=Network.objects.all(),
        distinct=True
    )
    id = MustIncludeThese()

    status = django_filters.MultipleChoiceFilter(
        choices=SiteLogStatus.choices,
        distinct=True
    )

    alert = django_filters.MultipleChoiceFilter(
        choices=[
            (alert.__name__, alert._meta.verbose_name.title())
            for alert in Alert.objects.site_alerts()
        ],
        method='filter_alerts',
        distinct=True
    )

    alert_level = EnumFilter(enum=AlertLevel, field_name='_max_alert')

    review_requested = django_filters.BooleanFilter(
        field_name='review_requested'
    )

    def filter_alerts(self, queryset, name, value):
        alert_q = Q()
        for alert in value:
            alert_q |= Q(
                **{f'{self.alert_fields[alert.lower()]}__isnull': False}
            )
        return queryset.filter(alert_q)

    class Meta:
        model = Site
        fields = (
            'name',
            'published_before',
            'published_after',
            'updated_before',
            'updated_after',
            'agency',
            'status',
            'network',
            'review_requested',
            'alert_level',
            'alert',
            'id'
        )
        distinct = True
