import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from slm.api.pagination import DataTablesPagination
from slm.api.public.serializers import (
    SiteFileUploadSerializer,
    StationListSerializer,
    ReceiverSerializer,
    AntennaSerializer,
    RadomeSerializer,
    ArchiveSerializer,
    AgencySerializer,
    NetworkSerializer
)
from slm.api.views import BaseSiteLogDownloadViewSet
from slm.models import (
    SiteFileUpload,
    SiteIndex,
    Receiver,
    Antenna,
    Radome,
    ArchivedSiteLog,
    Agency,
    Network
)
from slm.api.filter import SLMDateTimeFilter
from django.http import FileResponse
from slm.defines import SiteLogFormat
from django_enum.filters import EnumFilter
from django.utils.translation import gettext as _
from datetime import datetime


class DataTablesListMixin(mixins.ListModelMixin):
    """
    A mixin for adapting list views to work with the datatables library.
    """
    pagination_class = DataTablesPagination


class StationListViewSet(
    DataTablesListMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    
    serializer_class = StationListSerializer
    permission_classes = []
    lookup_field = 'site__name'
    lookup_url_kwarg = 'station'

    class StationFilter(FilterSet):

        name = django_filters.CharFilter(method='find_by_name')
        epoch = django_filters.DateTimeFilter(
            field_name='epoch',
            method='at_epoch'
        )
        agency = django_filters.CharFilter(
            field_name='agencies__name',
            lookup_expr='icontains'
        )
        search = django_filters.CharFilter(method='search_columns')

        def at_epoch(self, queryset, name, value):
            return queryset.at_epoch(epoch=value)

        def find_by_name(self, queryset, name, value):
            names = value.split(',')
            if len(names) == 1:
                return queryset.filter(site__name__istartswith=names[0])
            return queryset.filter(
                site__name__in=[name.upper() for name in names]
            )

        def search_columns(self, queryset, name, value):
            """
            Search multiple columns for the given value.
            """
            return queryset.filter(
                Q(site__name__istartswith=value) |
                Q(site__agencies__shortname__icontains=value) |
                Q(site__agencies__name__icontains=value) |
                Q(site__networks__name__icontains=value) |
                Q(city__icontains=value) |
                Q(country__icontains=value) |
                Q(antenna__model__icontains=value) |
                Q(radome__model__icontains=value) |
                Q(receiver__model__icontains=value) |
                Q(serial_number__icontains=value) |
                Q(firmware__icontains=value) |
                Q(frequency_standard__icontains=value) |
                Q(domes_number__icontains=value) |
                Q(satellite_system__name__icontains=value) |
                Q(data_center__icontains=value)
            ).distinct()

        class Meta:
            model = SiteIndex
            fields = (
                'name',
                'epoch',
                'agency',
                'search'
            )

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = StationFilter
    ordering_fields = [
        'site__name', 'country', 'agency', 'latitude', 'longitude', 'elevation'
    ]
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

    class FileFilter(FilterSet):

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


class ReceiverViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = ReceiverSerializer
    permission_classes = []

    class ReceiverFilter(FilterSet):
        model = django_filters.CharFilter(lookup_expr='istartswith')

        class Meta:
            model = Receiver
            fields = ('model',)

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

    class AntennaFilter(FilterSet):
        model = django_filters.CharFilter(lookup_expr='istartswith')

        class Meta:
            model = Antenna
            fields = ('model',)

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

    class RadomeFilter(FilterSet):
        model = django_filters.CharFilter(lookup_expr='istartswith')

        class Meta:
            model = Radome
            fields = ('model',)

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

    class AgencyFilter(FilterSet):
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

    class NetworkFilter(FilterSet):
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

    class ArchiveFilter(FilterSet):

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
