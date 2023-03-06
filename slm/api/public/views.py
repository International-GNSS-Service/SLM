import django_filters
from django.db.models import Q, Subquery, OuterRef
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from slm.api.pagination import DataTablesPagination
from slm.api.public.serializers import (
    SiteFileUploadSerializer,
    StationListSerializer,
    StationNameSerializer,
    ReceiverSerializer,
    AntennaSerializer,
    RadomeSerializer,
    ArchiveSerializer,
    AgencySerializer,
    NetworkSerializer,
    #DOMESSerializer
)
from slm.api.views import BaseSiteLogDownloadViewSet
from slm.models import (
    SiteFileUpload,
    Site,
    SiteIdentification,
    SiteIndex,
    Receiver,
    Antenna,
    Radome,
    ArchivedSiteLog,
    Agency,
    Network,
    SatelliteSystem
)
from slm.forms import PublicAPIStationFilterForm
from slm.api.filter import (
    SLMDateTimeFilter,
    AcceptListArguments
)
from slm.api.filter import SLMBooleanFilter, CrispyFormCompat
from django.http import FileResponse
from slm.defines import SiteLogFormat, ISOCountry, FrequencyStandardType
from django_enum.filters import EnumFilter
from django.utils.translation import gettext as _
from datetime import datetime


class StationFilter(CrispyFormCompat, AcceptListArguments, FilterSet):

    def get_form_class(self):
        return PublicAPIStationFilterForm

    @property
    def current_equipment(self):
        return self.form.cleaned_data.get('current', None)

    @property
    def query_epoch(self):
        return self.form.cleaned_data.get('epoch', datetime.now())

    epoch = django_filters.DateTimeFilter(
        field_name='epoch',
        method='at_epoch'
    )

    def at_epoch(self, queryset, name, value):
        return queryset.at_epoch(epoch=value)

    name = django_filters.CharFilter(
        field_name='site__name',
        lookup_expr='icontains',
        distinct=True
    )

    agency = django_filters.ModelMultipleChoiceFilter(
        field_name='site__agencies',
        queryset=Agency.objects.all()
    )

    network = django_filters.ModelMultipleChoiceFilter(
        field_name='site__networks',
        queryset=Network.objects.all()
    )

    station = django_filters.ModelMultipleChoiceFilter(
        field_name='site',
        queryset=Site.objects.all(),
        method='include_stations',
        null_value='',
        null_label=''
    )

    def include_stations(self, queryset, name, value):
        value = [val for val in value or [] if val]
        if value:
            queryset |= queryset.model.objects.at_epoch(
                self.query_epoch
            ).filter(**{f'{name}__in': value})
        return queryset

    receiver = django_filters.ModelMultipleChoiceFilter(
        method='filter_equipment',
        queryset=Receiver.objects.all()
    )

    antenna = django_filters.ModelMultipleChoiceFilter(
        method='filter_equipment',
        queryset=Antenna.objects.all()
    )

    radome = django_filters.ModelMultipleChoiceFilter(
        method='filter_equipment',
        queryset=Radome.objects.all()
    )

    satellite_system = django_filters.ModelMultipleChoiceFilter(
        method='filter_equipment',
        queryset=SatelliteSystem.objects.all()
    )

    frequency_standard = django_filters.MultipleChoiceFilter(
        choices=FrequencyStandardType.choices
    )

    country = django_filters.MultipleChoiceFilter(
        choices=ISOCountry.choices,
        distinct=True
    )

    current = SLMBooleanFilter(
        method='noop',
        distinct=True,
        field_name='current'
    )

    def noop(self, queryset, name, value):
        return queryset

    def filter_equipment(self, queryset, name, value):
        if value:
            if self.current_equipment:
                return queryset.filter(
                    Q(**{f'{name}__in': value}) &
                    SiteIndex.objects.epoch_q(self.query_epoch)
                ).distinct()
            else:
                return queryset.filter(site__in=Site.objects.filter(
                    **{f'indexes__{name}__in': value}
                ).distinct())
        return queryset

    class Meta:
        model = SiteIndex
        fields = (
            'station',
            'name',
            'agency',
            'network',
            'receiver',
            'antenna',
            'radome',
            'country',
            'current',
            'epoch',
            'satellite_system',
            'frequency_standard'
        )
        distinct = True


class DataTablesListMixin(mixins.ListModelMixin):
    """
    A mixin for adapting list views to work with the datatables library.
    """
    pagination_class = DataTablesPagination


class StationNameViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):

    queryset = Site.objects.public()
    serializer_class = StationNameSerializer
    permission_classes = []

    class StationNameFilter(CrispyFormCompat, FilterSet):
        """
        Todo chain with station filer.
        """

        name = django_filters.CharFilter(
            lookup_expr='icontains',
            distinct=True
        )

        class Meta:
            model = Site
            fields = ('name',)
            distinct = True

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = StationNameFilter
    ordering = ('name',)


class StationListViewSet(
    DataTablesListMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = StationListSerializer
    permission_classes = []
    lookup_field = 'site__name'
    lookup_url_kwarg = 'station'

    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)
    filterset_class = StationFilter
    ordering_fields = [
        'site__name', 'country', 'agency', 'latitude', 'longitude', 'elevation'
    ]
    
    search_fields = (
        'site__name',
        'site__agencies__name',
        'site__agencies__shortname',
        'site__networks__name',
        'city',
        'antenna__model',
        'radome__model',
        'receiver__model',
        'serial_number',
        'firmware',
        'domes_number',
        'satellite_system__name',
        'data_center'
    )
    ordering = ('site__name',)

    def get_queryset(self):
        return SiteIndex.objects.select_related(
            'site',
            'receiver',
            'antenna',
            'radome'
        ).prefetch_related(
            'site__agencies',
            'site__networks'
        ).public().at_epoch().availability()


class SiteLogDownloadViewSet(BaseSiteLogDownloadViewSet):
    # limit downloads to public sites only!
    # requests for non-public sites will return 404s
    pass


class SiteFileUploadViewSet(DataTablesListMixin, viewsets.GenericViewSet):
    serializer_class = SiteFileUploadSerializer
    permission_classes = []

    class FileFilter(CrispyFormCompat, FilterSet):

        site = django_filters.CharFilter(method='find_by_name')

        name = django_filters.CharFilter(
            field_name='name',
            lookup_expr='istartswith'
        )

        def find_by_name(self, queryset, name, value):
            return queryset.filter(site__name__istartswith=value)

        class Meta:
            model = SiteFileUpload
            fields = (
                'name',
                'site',
                'mimetype',
                'file_type'
            )

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = FileFilter
    ordering_fields = ['-timestamp', 'name', 'site']

    def get_queryset(self):
        return SiteFileUpload.objects.public().select_related('site')

"""
todo - waiting on DOMES data model change
class DOMESViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    serializer_class = DOMESSerializer
    permission_classes = []

    class DOMESFilter(FilterSet):
        model = django_filters.CharFilter(lookup_expr='icontains')
        in_use = django_filters.BooleanFilter(
            method='in_use_filter',
            distinct=True
        )

        def in_use_filter(self, queryset, name, value):
            if value:
                return queryset.filter(
                    site_receivers__isnull=False
                ).distinct()
            return queryset

        class Meta:
            model = Site
            fields = ('id', 'domes_')
            distinct = True

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = DOMESFilter
    ordering_fields = ('model',)
    ordering = ('model',)

    def get_queryset(self):
        return Site.objects.select_related('manufacturer')
"""


class ReceiverViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = ReceiverSerializer
    permission_classes = []

    class ReceiverFilter(CrispyFormCompat, FilterSet):
        model = django_filters.CharFilter(lookup_expr='icontains')
        in_use = django_filters.BooleanFilter(
            method='in_use_filter',
            distinct=True
        )

        def in_use_filter(self, queryset, name, value):
            if value:
                return queryset.filter(
                    site_receivers__isnull=False
                ).distinct()
            return queryset

        class Meta:
            model = Receiver
            fields = ('model', 'in_use')
            distinct = True

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = ReceiverFilter
    ordering_fields = ('model',)
    ordering = ('model',)

    def get_queryset(self):
        return Receiver.objects.select_related('manufacturer')


class AntennaViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = AntennaSerializer
    permission_classes = []

    class AntennaFilter(CrispyFormCompat, FilterSet):
        model = django_filters.CharFilter(lookup_expr='icontains')
        in_use = django_filters.BooleanFilter(
            method='in_use_filter',
            distinct=True
        )

        def in_use_filter(self, queryset, name, value):
            if value:
                return queryset.filter(
                    site_antennas__isnull=False
                ).distinct()
            return queryset

        class Meta:
            model = Antenna
            fields = ('model', 'in_use')
            distinct = True

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = AntennaFilter
    ordering_fields = ('model',)
    ordering = ('model',)

    def get_queryset(self):
        return Antenna.objects.select_related('manufacturer')


class RadomeViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = RadomeSerializer
    permission_classes = []

    class RadomeFilter(CrispyFormCompat, FilterSet):
        model = django_filters.CharFilter(lookup_expr='icontains')
        in_use = django_filters.BooleanFilter(
            method='in_use_filter',
            distinct=True
        )

        def in_use_filter(self, queryset, name, value):
            if value:
                return queryset.filter(
                    site_radomes__isnull=False
                ).distinct()
            return queryset

        class Meta:
            model = Radome
            fields = ('model',)
            distinct = True

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = RadomeFilter
    ordering_fields = ('model',)
    ordering = ('model',)

    def get_queryset(self):
        return Radome.objects.select_related('manufacturer')


class AgencyViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = AgencySerializer
    permission_classes = []

    class AgencyFilter(CrispyFormCompat, FilterSet):
        name = django_filters.CharFilter(lookup_expr='icontains')
        abbr = django_filters.CharFilter(
            lookup_expr='icontains',
            field_name='short_name'
        )

        search = django_filters.CharFilter(method='name_or_abbr')

        def name_or_abbr(self, queryset, name, value):
            return queryset.filter(
                Q(name__icontains=value) | Q(shortname__icontains=value)
            )

        class Meta:
            model = Agency
            fields = ('name', 'abbr', 'search')

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = AgencyFilter
    ordering_fields = ('name', 'shortname')
    ordering = ('name', 'shortname')

    def get_queryset(self):
        return Agency.objects.visible_to(self.request.user)


class NetworkViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = NetworkSerializer
    permission_classes = []

    class NetworkFilter(CrispyFormCompat, FilterSet):
        name = django_filters.CharFilter(lookup_expr='icontains')

        class Meta:
            model = Network
            fields = ('name',)

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = NetworkFilter
    ordering_fields = ('name',)
    ordering = ('name',)

    def get_queryset(self):
        return Network.objects.public()


class ArchiveViewSet(
    mixins.RetrieveModelMixin,
    DataTablesListMixin,
    viewsets.GenericViewSet
):
    serializer_class = ArchiveSerializer
    permission_classes = []

    class ArchiveFilter(CrispyFormCompat, FilterSet):

        site = django_filters.CharFilter(
            field_name='site__name',
            help_text=_(
                'The site of the archived log to download.'
            )
        )

        log_format = EnumFilter(
            enum=SiteLogFormat,
            help_text=_(
                'The format of the archived log to download.'
            )
        )

        epoch = SLMDateTimeFilter(
            method='at_epoch',
            initial=lambda: datetime.now(),
            help_text=_(
                'Get the archive that was active at this given date or '
                'datetime.'
            )
        )

        def at_epoch(self, queryset, name, value):
            return queryset.filter(
                Q(index__begin__lte=value) &
                (Q(index__end__isnull=True) | Q(index__end__gt=value))
            )

        class Meta:
            model = ArchivedSiteLog
            fields = ['site', 'epoch', 'log_format']

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = ArchiveFilter
    ordering_fields = ('timestamp',)
    ordering = ('-timestamp',)

    def retrieve(self, request, *args, **kwargs):
        archive = self.get_object()
        return FileResponse(archive.file, filename=archive.name)

    def get_queryset(self):
        return ArchivedSiteLog.objects.select_related('index', 'site')
