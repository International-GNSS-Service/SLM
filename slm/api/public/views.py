# stations view
from django.db.models import Q, Subquery, OuterRef, Exists
from slm.utils import to_bool
from rest_framework import mixins
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import (
    DjangoFilterBackend,
    FilterSet
)
import django_filters
from slm.defines import RinexVersion
from slm.api.public.serializers import StationListSerializer
from slm.api.views import BaseSiteLogDownloadViewSet
from django.db.models import ExpressionWrapper, F, Value, Case, When, DurationField, DateField
from django.db.models import IntegerField, F, Avg, fields, BooleanField
from django.db import models
from django.db.models.functions import Now, Cast, ExtractDay, TruncDate, Now, ExtractMonth, ExtractYear
from django.utils import timezone

from slm.models import (
    Site,
    SiteLocation,
    SiteAntenna,
    SiteReceiver,
    SiteFrequencyStandard,
    SiteIdentification,
    SiteMoreInformation,
    DataAvailability,
)
from slm.api.pagination import DataTablesPagination
from django.utils.timezone import now
from django.http import HttpResponse
from rest_framework import viewsets, renderers
from datetime import date
import datetime
from datetime import timedelta
import json


class PassThroughRenderer(renderers.BaseRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = ''
    format = 'legacy'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class LegacyRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to legacy format.
    """
    media_type = 'text/plain'
    format = 'text'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b''
        elif isinstance(data, dict):
            if 'detail' in data:
                return data['detail'].encode()
            return json.dumps(data)
        return data.encode()


class GMLRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to legacy format.
    """
    media_type = 'application/xml'
    format = 'xml'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b''
        return data.encode()


class JSONRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to legacy format.
    """
    media_type = 'application/json'
    format = 'xml'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b''
        return data.encode()


class DataTablesListMixin(mixins.ListModelMixin):
    """
    A mixin for adapting list views to work with the datatables library.
    """
    pagination_class = DataTablesPagination


class StationListViewSet(DataTablesListMixin, viewsets.GenericViewSet):
    
    serializer_class = StationListSerializer
    permission_classes = []

    class StationFilter(FilterSet):

        name = django_filters.CharFilter(method='find_by_name')
        published_before = django_filters.CharFilter(field_name='last_publish', lookup_expr='lt')
        published_after = django_filters.CharFilter(field_name='last_publish', lookup_expr='gte')
        agency = django_filters.CharFilter(field_name='agencies__name', lookup_expr='icontains')
        search = django_filters.CharFilter(method='search_columns')

        def find_by_name(self, queryset, name, value):
            names = value.split(',')
            if len(names) == 1:
                return queryset.filter(name__istartswith=names[0])
            return queryset.filter(
                name__in=[name.upper() for name in names]
            )

        def search_columns(self, queryset, name, value):
            """
            Search multiple columns for the given value.
            """
            return queryset.filter(
                Q(name__istartswith=value) |
                Q(agencies__shortname__icontains=value) |
                Q(agencies__name__icontains=value) |
                Q(latitude__icontains=value) |
                Q(longitude__icontains=value) |
                Q(city__icontains=value) |
                Q(country__icontains=value) |
                Q(elevation__icontains=value) |
                Q(antenna_type__icontains=value) |
                Q(radome_type__icontains=value) |
                Q(receiver_type__icontains=value) |
                Q(serial_number__icontains=value) |
                Q(firmware__icontains=value) |
                Q(frequency_standard__icontains=value) |
                Q(domes_number__icontains=value) |
                Q(satellite_system__icontains=value) |
                Q(data_center__icontains=value) 

            )

        class Meta:
            model = Site
            fields = (
                'name',
                'published_before',
                'published_after',
                'agency',
                'status',
                'search'
            )

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = StationFilter
    ordering_fields = ['name', 'country', 'agency', 'latitude', 'longitude', 'elevation']
    ordering = ('name',)

    def get_queryset(self):
        last_published_location = SiteLocation.objects.filter(
            site=OuterRef('pk'),
            published=True
        ).order_by('-edited')

        last_published_antenna = SiteAntenna.objects.filter(
            site=OuterRef('pk'),
            published=True
        ).order_by('-edited')

        last_published_receiver = SiteReceiver.objects.filter(
            site=OuterRef('pk'),
            published=True
        ).order_by('-edited')

        last_published_freq_standard = SiteFrequencyStandard.objects.filter(
            site=OuterRef('pk'),
            published=True
        ).order_by('-edited')

        last_published_iden = SiteIdentification.objects.filter(
            site=OuterRef('pk'),
            published=True
        ).order_by('-edited')

        last_published_info = SiteMoreInformation.objects.filter(
            site=OuterRef('pk'),
            published=True
        ).order_by('-edited')

        last_data_avail = DataAvailability.objects.filter(
            site=OuterRef('pk')
        ).order_by('-last')

        from django.db.models.functions import Now
        """

        last_data_1=ExpressionWrapper(((ExtractYear(now().date()) - (ExtractYear('rinex2')))*12*30) + 
                                ((ExtractMonth(now().date()) - (ExtractMonth('rinex2')))*30) + 
                                ((ExtractDay(now().date()) - (ExtractDay('rinex2')))) , models.IntegerField())

        last_data_2=ExpressionWrapper(((ExtractYear(now().date()) - (ExtractYear('rinex3')))*12*30) + 
                            ((ExtractMonth(now().date()) - (ExtractMonth('rinex3')))*30) + 
                            ((ExtractDay(now().date()) - (ExtractDay('rinex3')))) , models.IntegerField())
        """

        return Site.objects.public().prefetch_related('agencies', 'networks').annotate(
            latitude=Subquery(last_published_location.values('latitude')[:1]),
            longitude=Subquery(last_published_location.values('longitude')[:1]),
            city=Subquery(last_published_location.values('city')[:1]),
            country=Subquery(last_published_location.values('country')[:1]),
            elevation=Subquery(last_published_location.values('elevation')[:1]),
            antenna_type=Subquery(last_published_antenna.values('antenna_type')[:1]),
            radome_type=Subquery(last_published_antenna.values('radome_type')[:1]),
            receiver_type=Subquery(last_published_receiver.values('receiver_type')[:1]),
            serial_number=Subquery(last_published_receiver.values('serial_number')[:1]),
            firmware=Subquery(last_published_receiver.values('firmware')[:1]),
            frequency_standard=Subquery(last_published_freq_standard.values('standard_type')[:1]),
            domes_number=Subquery(last_published_iden.values('iers_domes_number')[:1]),
            satellite_system=Subquery(last_published_receiver.values('satellite_system')[:1]),
            data_center=Subquery(last_published_info.values('primary')[:1]),
            last_data_time=Subquery(last_data_avail.values('last')[:1]),
            last_data=Now() - F('last_data_time'),
            last_rinex2=Subquery(
                last_data_avail.filter(
                    RinexVersion(2).major_q()
                ).values('last')[:1]),
            last_rinex3=Subquery(
                last_data_avail.filter(
                    RinexVersion(3).major_q()
                ).values('last')[:1]),
            last_rinex4=Subquery(
                last_data_avail.filter(
                    RinexVersion(4).major_q()
                ).values('last')[:1]),
        )


class SiteLogDownloadViewSet(BaseSiteLogDownloadViewSet):
    # limit downloads to public sites only! requests for non-public sites will
    # return 404s, also use legacy four id naming, revisit this?
    queryset = Site.objects.public()
