# stations view
import json

import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, renderers, viewsets
from rest_framework.filters import OrderingFilter
from slm.api.pagination import DataTablesPagination
from slm.api.public.serializers import (
    SiteFileUploadSerializer,
    StationListSerializer,
)
from slm.api.views import BaseSiteLogDownloadViewSet
from slm.models import Site, SiteFileUpload, SiteIndex


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
    # limit downloads to public sites only! requests for non-public sites will
    # return 404s, also use legacy four id naming, revisit this?
    queryset = Site.objects.public()


class SiteFileUploadViewSet(DataTablesListMixin, viewsets.GenericViewSet):
    serializer_class = SiteFileUploadSerializer
    permission_classes = []

    class FileFilter(FilterSet):

        site = django_filters.CharFilter(
            method='find_by_name'
        )

        name = django_filters.CharFilter(
            field_name='name',
            lookup_expr='istartswith'
        )

        def find_by_name(self, queryset, name, value):
            return queryset.filter(
                site__name__istartswith=value
            )

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
    ordering_fields = [
        '-timestamp',
        'name',
        'site'
    ]

    def get_queryset(self):
        return SiteFileUpload.objects.public().select_related('site')
