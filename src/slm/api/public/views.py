import json
from datetime import datetime, timezone

import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Fieldset, Layout, Submit
from django import forms
from django.db.models import Prefetch, Q
from django.http import FileResponse
from django.utils.translation import gettext as _
from django_enum.filters import EnumFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter

from slm.api.filter import (
    BaseStationFilter,
    CrispyFormCompat,
    SiteSearchFilter,
    SLMBooleanFilter,
    SLMDateTimeFilter,
)
from slm.api.pagination import DataTablesPagination
from slm.api.public.serializers import (  # DOMESSerializer
    AgencySerializer,
    AntennaSerializer,
    ArchiveSerializer,
    ManufacturerSerializer,
    NetworkSerializer,
    RadomeSerializer,
    ReceiverSerializer,
    SiteFileUploadSerializer,
    StationListSerializer,
    StationNameSerializer,
)
from slm.api.views import BaseSiteLogDownloadViewSet
from slm.defines import EquipmentState, SiteLogFormat, SiteLogStatus
from slm.forms import EnumMultipleChoiceField, SLMBooleanField
from slm.forms import StationFilterForm as BaseStationFilterForm
from slm.models import (
    Agency,
    Antenna,
    ArchivedSiteLog,
    Equipment,
    Manufacturer,
    Network,
    Radome,
    Receiver,
    Site,
    SiteFileUpload,
    SiteReceiver,
    SiteTideGauge,
)


class StationFilterForm(BaseStationFilterForm):
    include_former = SLMBooleanField(
        label=_("Include Former"),
        help_text=_(
            "Include stations that are no longer maintained as part of any "
            "of our networks."
        ),
        initial=False,
        required=False,
    )

    include_proposed = SLMBooleanField(
        label=_("Include Proposed"),
        help_text=_(
            "Include stations that are proposed for future inclusion in one "
            "of our networks."
        ),
        initial=False,
        required=False,
    )

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_method = "GET"
        helper.disable_csrf = True
        helper.form_id = "slm-station-filter"
        helper.layout = Layout(
            Div(
                Div(
                    "station",
                    Field("satellite_system", wrapper_class="form-switch"),
                    Field("frequency_standard", wrapper_class="form-switch"),
                    css_class="col-3",
                ),
                Div(
                    Fieldset(
                        _("Equipment Filters"),
                        Field("current", wrapper_class="form-switch"),
                        "receiver",
                        "antenna",
                        "radome",
                        css_class="slm-form-group",
                    ),
                    css_class="col-4",
                ),
                Div(
                    "agency",
                    "network",
                    Field("country", css_class="slm-country search-input"),
                    Field("include_former", wrapper_class="form-switch"),
                    Field("include_proposed", wrapper_class="form-switch"),
                    "geography",
                    css_class="col-5",
                ),
                css_class="row",
            ),
            Submit("", _("Submit"), css_class="btn btn-primary"),
        )
        helper.attrs = {
            "data_slm_initial": json.dumps(
                {
                    field.name: field.field.initial
                    for field in self
                    if field.field.initial
                }
            )
        }
        return helper


class StationFilter(BaseStationFilter):
    include_former = SLMBooleanFilter(
        method="filter_former", field_name="include_former"
    )

    include_proposed = SLMBooleanFilter(
        method="filter_proposed", field_name="include_proposed"
    )

    def filter_former(self, queryset, name, value):
        if not value:
            return queryset.filter(~Q(status=SiteLogStatus.FORMER))
        return queryset

    def filter_proposed(self, queryset, name, value):
        if not value:
            return queryset.filter(~Q(status=SiteLogStatus.PROPOSED))
        return queryset

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
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Site.objects.public()
    serializer_class = StationNameSerializer
    permission_classes = []

    class StationNameFilter(CrispyFormCompat, FilterSet):
        """
        Todo chain with station filer.
        """

        name = django_filters.CharFilter(lookup_expr="icontains", distinct=True)

        class Meta:
            model = Site
            fields = ("name",)
            distinct = True

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = StationNameFilter
    ordering = ("name",)


class StationListViewSet(
    DataTablesListMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = StationListSerializer
    permission_classes = []
    lookup_field = "name"
    lookup_url_kwarg = "station"

    filter_backends = (DjangoFilterBackend, OrderingFilter, SiteSearchFilter)

    filterset_class = StationFilter
    ordering_fields = [
        "name",
        "last_data",  # 'lat', 'lon', 'elev',
    ]

    # if you update these you have to also update
    search_fields = (
        "name",
        "agencies__name",
        "agencies__shortname",
        "networks__name",
        "sitelocation__city",
        "sitereceiver__serial_number",
        "sitereceiver__firmware",
        "siteidentification__iers_domes_number",
        "sitemoreinformation__primary",
        "siteantenna__antenna_type__model",
        "siteantenna__radome_type__model",
        "sitereceiver__receiver_type__model",
    )
    ordering = ("name",)

    def get_queryset(self):
        return (
            Site.objects.prefetch_related(
                "agencies",
                "networks",
                Prefetch(
                    "sitereceiver_set",
                    queryset=SiteReceiver.objects.published()
                    .prefetch_related("satellite_system")
                    .order_by("-installed"),
                ),
                Prefetch(
                    "tide_gauge_distances",
                    queryset=SiteTideGauge.objects.prefetch_related("gauge").order_by(
                        "-distance"
                    ),
                ),
            )
            .with_location_fields("city", "state", "country", "xyz", "llh")
            .with_identification_fields("cdp_number", iers_domes_number="domes_number")
            .with_antenna_fields(
                "antcal",
                antenna_type__model="antenna_type",
                radome_type__model="radome_type",
                serial_number="antenna_serial_number",
                marker_une="antenna_marker_une",
            )
            .with_receiver_fields(
                "firmware",
                "serial_number",
                receiver_type__model="receiver_type",
            )
            .with_frequency_standard_fields(standard_type="frequency_standard")
            .with_info_fields(primary="data_center")
            .public()
            .availability()
            .distinct()
        )


class SiteLogDownloadViewSet(BaseSiteLogDownloadViewSet):
    # limit downloads to public sites only!
    # requests for non-public sites will return 404s
    pass


class SiteFileUploadViewSet(
    DataTablesListMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = SiteFileUploadSerializer
    permission_classes = []

    class FileFilter(CrispyFormCompat, FilterSet):
        site = django_filters.CharFilter(method="find_by_name")

        name = django_filters.CharFilter(field_name="name", lookup_expr="istartswith")

        def find_by_name(self, queryset, name, value):
            return queryset.filter(site__name__istartswith=value)

        class Meta:
            model = SiteFileUpload
            fields = ("name", "site", "mimetype", "file_type")

    def retrieve(self, request, *args, **kwargs):
        """
        A function view for downloading files that have been uploaded to
        a site. This allows unathenticated downloads of public files and
        authenticated download of any file available to the authenticated user.

        :param request: Django request object
        :return: Either a 404 or a FileResponse object containing the file.
        """

        file = self.get_object()
        if request.GET.get("thumbnail", None):
            file = file.thumbnail
        else:
            file = file.file
        return FileResponse(
            file.open("rb"),
            filename=file.name,
            # note this might not match the name on disk
            as_attachment=True,
        )

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = FileFilter
    ordering_fields = ("timestamp", "name", "site")

    def get_queryset(self):
        return SiteFileUpload.objects.public().select_related("site")


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


class EquipmentFilterForm(CrispyFormCompat, forms.Form):
    model = forms.CharField(required=False)

    state = EnumMultipleChoiceField(
        EquipmentState,
        help_text=_("Include equipment codings in these states."),
        label=_("Coding Status"),
        required=False,
    )
    in_use = forms.BooleanField(
        required=False,
        help_text=_("Only equipment that is in active use."),
        label=_("In Use"),
    )

    manufacturer = forms.CharField(required=False)


class EquipmentFilter(CrispyFormCompat, FilterSet):
    model = django_filters.CharFilter(lookup_expr="icontains")
    in_use = django_filters.BooleanFilter(
        method="in_use_filter", distinct=True, label="In Use"
    )
    manufacturer = django_filters.CharFilter(method="manufacturer_filter")
    state = django_filters.MultipleChoiceFilter(
        choices=EquipmentState.choices, distinct=True
    )
    related_formfield = None

    def manufacturer_filter(self, queryset, name, value):
        if value:
            return queryset.filter(manufacturer__name__icontains=value).distinct()
        return queryset

    def in_use_filter(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(**{f"{self.related_formfield}__isnull": False})
                & Q(**{f"{self.related_formfield}__published": True})
                & Q(**{f"{self.related_formfield}__removed__isnull": True})
                & Q(
                    **{
                        f"{self.related_formfield}__site__status__in": SiteLogStatus.active_states()
                    }
                )
            ).distinct()
        return queryset

    def get_form_class(self):
        return EquipmentFilterForm

    def filter_queryset(self, queryset):
        """
        By default
        """
        qryst = super().filter_queryset(queryset)
        if self.data.get("state", None):
            return qryst
        return qryst.filter(state=EquipmentState.ACTIVE)

    class Meta:
        model = Equipment
        fields = ("model", "in_use", "manufacturer", "state")
        distinct = True


class ReceiverViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = ReceiverSerializer
    permission_classes = []

    class ReceiverFilter(EquipmentFilter):
        related_formfield = "site_receivers"

        class Meta(EquipmentFilter.Meta):
            model = Receiver

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = ReceiverFilter
    ordering_fields = ("model",)
    ordering = ("model",)

    def get_queryset(self):
        return Receiver.objects.select_related("manufacturer").prefetch_related(
            "replaced"
        )


class AntennaViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = AntennaSerializer
    permission_classes = []

    class AntennaFilter(EquipmentFilter):
        related_formfield = "site_antennas"

        class Meta(EquipmentFilter.Meta):
            model = Antenna

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = AntennaFilter
    ordering_fields = ("model",)
    ordering = ("model",)

    def get_queryset(self):
        return Antenna.objects.select_related("manufacturer").prefetch_related(
            "replaced"
        )


class RadomeViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = RadomeSerializer
    permission_classes = []

    class RadomeFilter(EquipmentFilter):
        related_formfield = "site_radomes"

        class Meta(EquipmentFilter.Meta):
            model = Radome

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = RadomeFilter
    ordering_fields = ("model",)
    ordering = ("model",)

    def get_queryset(self):
        return Radome.objects.select_related("manufacturer").prefetch_related(
            "replaced"
        )


class ManufacturerViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = ManufacturerSerializer
    permission_classes = []

    class ManufacturerFilter(CrispyFormCompat, FilterSet):
        name = django_filters.CharFilter(lookup_expr="icontains")

        class Meta:
            model = Manufacturer
            fields = ("name",)
            distinct = True

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = ManufacturerFilter
    ordering_fields = ("name",)
    ordering = ("name",)

    def get_queryset(self):
        return Manufacturer.objects.all()


class AgencyViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = AgencySerializer
    permission_classes = []

    class AgencyFilter(CrispyFormCompat, FilterSet):
        name = django_filters.CharFilter(lookup_expr="icontains")
        abbr = django_filters.CharFilter(
            lookup_expr="icontains", field_name="short_name"
        )

        search = django_filters.CharFilter(method="name_or_abbr")

        def name_or_abbr(self, queryset, name, value):
            return queryset.filter(
                Q(name__icontains=value) | Q(shortname__icontains=value)
            )

        class Meta:
            model = Agency
            fields = ("name", "abbr", "search")

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = AgencyFilter
    ordering_fields = ("name", "shortname")
    ordering = ("name", "shortname")

    def get_queryset(self):
        return Agency.objects.visible_to(self.request.user)


class NetworkViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = NetworkSerializer
    permission_classes = []

    class NetworkFilter(CrispyFormCompat, FilterSet):
        name = django_filters.CharFilter(lookup_expr="icontains")

        class Meta:
            model = Network
            fields = ("name",)

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = NetworkFilter
    ordering_fields = ("name",)
    ordering = ("name",)

    def get_queryset(self):
        return Network.objects.public()


class ArchiveViewSet(
    mixins.RetrieveModelMixin, DataTablesListMixin, viewsets.GenericViewSet
):
    serializer_class = ArchiveSerializer
    permission_classes = []

    class ArchiveFilter(CrispyFormCompat, FilterSet):
        NULL_EPOCH = datetime.max.replace(tzinfo=timezone.utc)

        site = django_filters.CharFilter(
            field_name="site__name",
            help_text=_("The site of the archived log to download."),
        )

        log_format = EnumFilter(
            enum=SiteLogFormat,
            help_text=_("The format of the archived log to download."),
        )

        epoch = SLMDateTimeFilter(
            method="at_epoch",
            initial=NULL_EPOCH,
            help_text=_(
                "Get the archive that was active at this given date or datetime."
            ),
        )

        def at_epoch(self, queryset, name, value):
            if value == self.NULL_EPOCH:
                return queryset.order_by("-valid_range")[:1]
            else:
                return queryset.filter(valid_range__contains=value)

        class Meta:
            model = ArchivedSiteLog
            fields = ["site", "epoch", "log_format"]

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = ArchiveFilter
    ordering_fields = ("timestamp",)
    ordering = ("-timestamp",)

    def retrieve(self, request, *args, **kwargs):
        archive = self.get_object()
        return FileResponse(archive.file, filename=archive.name)

    def get_queryset(self):
        return ArchivedSiteLog.objects.select_related("index", "site")
