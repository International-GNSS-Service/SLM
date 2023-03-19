import django_filters
from django.db.models import Q, Subquery, OuterRef, Prefetch
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
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
    SiteLocation,
    SiteAntenna,
    SiteReceiver,
    SiteFrequencyStandard,
    SiteMoreInformation,
    Receiver,
    Antenna,
    Radome,
    ArchivedSiteLog,
    Agency,
    Network,
    SatelliteSystem,
    SiteTideGauge,
    AntCal
)
from slm.api.filter import (
    SLMDateTimeFilter,
    AcceptListArguments,
    SiteSearchFilter
)
from slm.api.filter import (
    SLMBooleanFilter,
    CrispyFormCompat,
    BaseStationFilter
)
from django.http import FileResponse
from slm.defines import SiteLogFormat, ISOCountry, FrequencyStandardType
from slm.forms import StationFilterForm as BaseStationFilterForm
from django_enum.filters import EnumFilter
from django.utils.translation import gettext as _
from datetime import datetime
from crispy_forms.layout import Layout, Div, Field, Fieldset, Submit
from crispy_forms.helper import FormHelper
import json


class StationFilterForm(BaseStationFilterForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_method = 'GET'
        helper.disable_csrf = True
        helper.form_id = 'slm-station-filter'
        helper.layout = Layout(
            Div(
                Div(
                    'station',
                    Field(
                        'satellite_system',
                        wrapper_class="form-switch"
                    ),
                    Field(
                        'frequency_standard',
                        wrapper_class="form-switch"
                    ),
                    css_class='col-3'
                ),
                Div(
                    Fieldset(
                        _('Equipment Filters'),
                        Field(
                            'current',
                            wrapper_class="form-switch"
                        ),
                        'receiver',
                        'antenna',
                        'radome',
                        css_class='slm-form-group'
                    ),
                    css_class='col-4'
                ),
                Div(
                    'agency',
                    'network',
                    Field('country', css_class='slm-country search-input'),
                    css_class='col-5'
                ),
                css_class='row',
            ),
            Submit('', _('Submit'), css_class='btn btn-primary')
        )
        helper.attrs = {'data_slm_initial': json.dumps({
            field.name: field.field.initial
            for field in self if field.field.initial
        })}
        return helper


class StationFilter(BaseStationFilter):

    def get_form_class(self):
        return StationFilterForm

    @property
    def restrict_published(self):
        return True


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
    lookup_field = 'name'
    lookup_url_kwarg = 'station'

    filter_backends = (
        DjangoFilterBackend,
        OrderingFilter,
        SiteSearchFilter
    )

    filterset_class = StationFilter
    ordering_fields = [
        'name', 'latitude', 'longitude', 'elevation', 'last_data'
    ]

    # if you update these you have to also update
    search_fields = (
        'name',
        'agencies__name',
        'agencies__shortname',
        'networks__name',
        'sitelocation__city',
        'sitereceiver__serial_number',
        'sitereceiver__firmware',
        'siteidentification__iers_domes_number',
        'sitemoreinformation__primary',
        'siteantenna__antenna_type__model',
        'siteantenna__radome_type__model',
        'sitereceiver__receiver_type__model'
    )
    ordering = ('name',)

    def get_queryset(self):
        antcal = AntCal.objects.filter(
            Q(antenna=OuterRef('antenna_type')) &
            Q(radome=OuterRef('radome_type'))
        )
        location = SiteLocation.objects.filter(
            Q(site=OuterRef('pk')) & Q(published=True)
        )
        identification = SiteIdentification.objects.filter(
            Q(site=OuterRef('pk')) & Q(published=True)
        )
        antenna = SiteAntenna.objects.filter(
            Q(site=OuterRef('pk')) & Q(published=True)
        ).annotate(calibration=Subquery(antcal.values('calibration')[:1]))

        receiver = SiteReceiver.objects.filter(
            Q(site=OuterRef('pk')) & Q(published=True)
        )
        info = SiteMoreInformation.objects.filter(
            Q(site=OuterRef('pk')) & Q(published=True)
        )
        freq = SiteFrequencyStandard.objects.filter(
            Q(site=OuterRef('pk')) & Q(published=True)
        )

        annotations = {
            'latitude': Subquery(location.values('latitude')[:1]),
            'longitude': Subquery(location.values('longitude')[:1]),
            'elevation': Subquery(location.values('elevation')[:1]),
            'city': Subquery(location.values('city')[:1]),
            'state': Subquery(location.values('state')[:1]),
            'country': Subquery(location.values('country')[:1]),
            'domes_number': Subquery(
                identification.values('iers_domes_number')[:1]
            ),
            'cdp_number': Subquery(
                identification.values('cdp_number')[:1]
            ),
            'antenna_type': Subquery(
                antenna.values('antenna_type__model')[:1]
            ),
            'radome_type': Subquery(
                antenna.values('radome_type__model')[:1]
            ),
            'antcal': Subquery(
                antenna.values('calibration')[:1]
            ),
            'receiver_type': Subquery(
                receiver.values('receiver_type__model')[:1]
            ),
            'serial_number': Subquery(
                receiver.values('serial_number')[:1]
            ),
            'firmware': Subquery(
                receiver.values('firmware')[:1]
            ),
            'frequency_standard': Subquery(
                freq.values('standard_type')[:1]
            ),
            'data_center': Subquery(
                info.values('primary')[:1]
            )
        }

        return Site.objects.prefetch_related(
            'agencies',
            'networks',
            Prefetch(
                'sitereceiver_set',
                queryset=SiteReceiver.objects.published().prefetch_related(
                    'satellite_system'
                )
            ),
            Prefetch(
                'tide_gauge_distances',
                queryset=SiteTideGauge.objects.prefetch_related(
                    'gauge'
                ).order_by('-distance')
            )
        ).annotate(**annotations).public().availability()


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
