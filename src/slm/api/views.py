from datetime import datetime, timezone

from django.http import FileResponse
from django.utils.translation import gettext as _
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, renderers, viewsets
from rest_framework.generics import get_object_or_404

from slm.api.filter import InitialValueFilterSet, SLMDateTimeFilter
from slm.defines import SiteLogFormat
from slm.models import ArchivedSiteLog, ArchiveIndex


class LegacyRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to legacy format.
    """

    media_type = SiteLogFormat.LEGACY.mimetype
    format = SiteLogFormat.LEGACY

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return b""


class ASCIIRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to legacy format.
    """

    media_type = SiteLogFormat.ASCII_9CHAR.mimetype
    format = SiteLogFormat.ASCII_9CHAR

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return b""


class GeodesyMLRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to GeodesyML format.
    """

    media_type = SiteLogFormat.GEODESY_ML.mimetype
    format = SiteLogFormat.GEODESY_ML

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return b""


class JSONRenderer(renderers.BaseRenderer):
    """
    Renderer which serializes to GeodesyML format.
    """

    media_type = SiteLogFormat.JSON.mimetype
    format = SiteLogFormat.JSON

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return b""


class BaseSiteLogDownloadViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    renderer_classes = [ASCIIRenderer, LegacyRenderer, GeodesyMLRenderer]

    site = None

    lookup_field = "site__name__istartswith"
    lookup_url_kwarg = "site"

    queryset = ArchiveIndex.objects.all()

    class ArchiveIndexFilter(InitialValueFilterSet):
        NULL_EPOCH = datetime.max.replace(tzinfo=timezone.utc)

        epoch = SLMDateTimeFilter(
            method="at_epoch",
            initial=NULL_EPOCH,
            help_text=_("Get the log that was active at this given date or datetime."),
        )

        name_len = filters.NumberFilter(
            method="noop",
            help_text=_(
                "The number of characters to include in the filename from the "
                "start of the 9 character site name."
            ),
        )

        lower_case = filters.BooleanFilter(
            method="noop", help_text=_("If true filename will be lowercase.")
        )

        def at_epoch(self, queryset, name, value):
            if value == self.NULL_EPOCH:
                # # this does not work because it pulls the most recent site log *first* - would need to
                # # do this after the site log filter!
                # last_index =  Subquery(
                #     queryset.order_by(Func('valid_range', function='lower').desc())
                #             .values('valid_range')[:1]
                # )
                # return queryset.filter(valid_range=last_index)
                return queryset.order_by("-valid_range")[:1]
            else:
                return queryset.filter(valid_range__contains=value)

        def noop(self, queryset, _1, _2):
            return queryset

        class Meta:
            model = ArchiveIndex
            fields = ["name_len", "epoch", "lower_case"]

    filter_backends = (DjangoFilterBackend,)
    filterset_class = ArchiveIndexFilter

    def get_object(self):
        """
        We override get_object so we can apply the station lookup first to the queryset.

        This is necessary because the at_epoch query uses a subquery.
        """
        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (self.__class__.__name__, lookup_url_kwarg)
        )

        obj = get_object_or_404(
            self.filter_queryset(
                self.get_queryset().filter(
                    **{self.lookup_field: self.kwargs[lookup_url_kwarg]}
                )
            )
        )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_format_suffix(self, **kwargs):
        requested_format = super().get_format_suffix(**kwargs)

        # if the site name is a 4-id return the old 4char log format
        if "site" in kwargs and len(kwargs["site"]) == 4 and requested_format == "log":
            return SiteLogFormat.LEGACY

        # match suffix first
        for fmt in reversed(SiteLogFormat):
            if fmt.ext == requested_format:
                return fmt

        # if that fails accept alts by priority
        return SiteLogFormat(requested_format)

    def retrieve(self, request, *args, **kwargs):
        """
        Download the site log rendered in the specified format - preferencing
        the HTTP_ACCEPTS header over the format parameter. In most cases
        from_site will fetch the archived log from disk, but if a format that
        was not previously rendered is requested from_site might first create
        a new ArchivedSiteLog. If no index is found and allow_unpublished is
        true a new site log will be rendered from the current HEAD state.

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        index = self.get_object()
        archived = ArchivedSiteLog.objects.from_index(
            index=index, log_format=request.accepted_renderer.format
        )
        return FileResponse(
            archived.file,
            filename=index.site.get_filename(
                log_format=archived.log_format,
                epoch=index.begin,
                name_len=request.GET.get("name_len", None),
                lower_case=request.GET.get("lower_case", False),
            ),
        )
