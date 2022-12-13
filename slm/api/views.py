import json

from django.http import HttpResponse
from django.utils.translation import gettext as _
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, renderers, viewsets
from slm.api.serializers import SiteLogSerializer
from slm.models import Site
from slm.utils import to_bool
from slm.defines import SiteLogFormat


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


class BaseSiteLogDownloadViewSet(
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Site.objects

    lookup_field = 'name'
    lookup_url_kwarg = 'site'
    renderer_classes = (LegacyRenderer, GMLRenderer)

    class DownloadFilter(FilterSet):

        name_len = filters.NumberFilter()
        name_len.help = _(
            'The number of characters to include in the filename from the '
            'start of the 9 character site name.'
        )

        epoch = filters.DateTimeFilter()
        epoch.help = _(
            'Get the log that was published at this given date or datetime.'
        )

        lower_case = filters.BooleanFilter()
        lower_case.help = _('If true filename will be lowercase.')

        published_default = True

        def filter_queryset(self, queryset):
            return queryset.annotate_filenames(
                **{
                    # may be overridden below
                    **{'published': True},
                    **{
                        param: val for param, val in
                        self.form.cleaned_data.items()
                        if param in ['lower_case', 'name_len', 'published']
                    }
                }
            )

        class Meta:
            model = Site
            fields = ['name_len', 'epoch', 'lower_case']

    filter_backends = (DjangoFilterBackend,)
    filterset_class = DownloadFilter

    serializer_class = SiteLogSerializer

    def retrieve(self, request, *args, **kwargs):
        site = self.get_object()
        format = {
            'text': SiteLogFormat.LEGACY,
            'xml': SiteLogFormat.GEODESY_ML,
            'json': SiteLogFormat.JSON
        }.get(kwargs.get('format', 'text'), SiteLogFormat.LEGACY)
        serializer = self.get_serializer(
            instance=site,
            epoch=self.request.GET.get('epoch', None),
            published=to_bool(
                self.request.GET.get('published', True)
            ) or None
        )
        response = HttpResponse(serializer.format(log_format=format))

        if (
            to_bool(kwargs.get('download', True)) and
            response.status_code < 400
        ):
            response['Content-Disposition'] = (
                f'attachment; filename={site.filename}.{format.ext}'
            )
        return response
