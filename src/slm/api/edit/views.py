import json
from datetime import datetime
from io import BytesIO
from logging import getLogger

import django_filters
from chardet import detect
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Fieldset, Layout
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.db.models import Q
from django.http import Http404
from django.http.response import (
    FileResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django_enum.drf import EnumField
from django_enum.fields import (
    EnumBigIntegerField,
    EnumCharField,
    EnumIntegerField,
    EnumPositiveBigIntegerField,
    EnumPositiveIntegerField,
    EnumPositiveSmallIntegerField,
    EnumSmallIntegerField,
)
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, renderers, serializers, status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import (
    FileUploadParser,
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, SlugRelatedField

from slm import signals as slm_signals
from slm.api.edit.serializers import (
    AlertSerializer,
    LogEntrySerializer,
    ReviewRequestSerializer,
    SiteFileUploadSerializer,
    StationSerializer,
    UserSerializer,
)
from slm.api.fields import SLMDateTimeField, SLMPointField
from slm.api.filter import (
    AcceptListArguments,
    BaseStationFilter,
    CrispyFormCompat,
    SLMBooleanFilter,
)
from slm.api.pagination import DataTablesPagination
from slm.api.permissions import (
    CanDeleteAlert,
    CanEditSite,
    CanRejectReview,
    IsUserOrAdmin,
    VerifyModerationActions,
)
from slm.api.public.views import AgencyViewSet as PublicAgencyViewSet
from slm.api.public.views import NetworkViewSet as PublicNetworkViewSet
from slm.api.serializers import SiteLogSerializer
from slm.api.views import BaseSiteLogDownloadViewSet
from slm.defines import (
    CardinalDirection,
    CoordinateMode,
    SiteFileUploadStatus,
    SiteLogFormat,
    SiteLogStatus,
    SLMFileType,
)
from slm.forms import StationFilterForm as BaseStationFilterForm
from slm.models import (
    Agency,
    Alert,
    LogEntry,
    Network,
    Site,
    SiteAntenna,
    SiteCollocation,
    SiteFileUpload,
    SiteForm,
    SiteFrequencyStandard,
    SiteHumiditySensor,
    SiteIdentification,
    SiteLocalEpisodicEffects,
    SiteLocation,
    SiteMoreInformation,
    SiteMultiPathSources,
    SiteOperationalContact,
    SiteOtherInstrumentation,
    SitePressureSensor,
    SiteRadioInterferences,
    SiteReceiver,
    SiteResponsibleAgency,
    SiteSection,
    SiteSignalObstructions,
    SiteSubSection,
    SiteSurveyedLocalTies,
    SiteTemperatureSensor,
    SiteWaterVaporRadiometer,
)
from slm.parsing.legacy.parser import Error, Warn
from slm.utils import llh2xyz, xyz2llh


class StationFilterForm(BaseStationFilterForm):
    @property
    def helper(self):
        """
        Todo - how to render help_text as alt or titles?
        """
        helper = FormHelper()
        helper.form_id = "slm-station-filter"
        helper.disable_csrf = True
        helper.layout = Layout(
            Div(
                Div(
                    Field("status", css_class="slm-status"),
                    "alert",
                    Field("alert_level", css_class="slm-alert-level"),
                    css_class="col-3",
                ),
                Div(
                    Fieldset(
                        _("Equipment Filters"),
                        Field(
                            "current",
                            css_class="form-check-input",
                            wrapper_class="form-check form-switch",
                        ),
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
                    css_class="col-5",
                ),
                css_class="row",
            )
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
    """
    Edit API station filter extensions.
    """

    def get_form_class(self):
        return StationFilterForm

    @property
    def current_equipment(self):
        return self.form.cleaned_data.get("current", None)


class PassThroughRenderer(renderers.BaseRenderer):
    """
    Return data as-is. View should supply a Response.
    """

    media_type = ""
    format = "legacy"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class DataTablesListMixin(mixins.ListModelMixin):
    """
    A mixin for adapting list views to work with the datatables library.
    """

    pagination_class = DataTablesPagination


class AgencyViewSet(PublicAgencyViewSet):
    def get_queryset(self):
        return Agency.objects.membership(self.request.user)


class NetworkViewSet(PublicNetworkViewSet):
    def get_queryset(self):
        return Network.objects.visible_to(self.request.user)


class ReviewRequestView(
    DataTablesListMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReviewRequestSerializer
    permission_classes = (IsAuthenticated, CanEditSite)

    def perform_update(self, serializer):
        slm_signals.review_requested.send(
            sender=self,
            site=serializer.instance,
            detail=serializer.validated_data.get("detail", None),
            request=self.request,
        )
        serializer.instance.refresh_from_db()

    def get_queryset(self):
        return (
            Site.objects.editable_by(self.request.user)
            .filter(review_requested__isnull=True)
            .filter(status__in=SiteLogStatus.unpublished_states())
        )


class RejectUpdatesView(
    DataTablesListMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReviewRequestSerializer
    permission_classes = (IsAuthenticated, CanRejectReview)

    def perform_update(self, serializer):
        slm_signals.updates_rejected.send(
            sender=self,
            site=serializer.instance,
            detail=serializer.validated_data.get("detail", None),
            request=self.request,
        )
        serializer.instance.refresh_from_db()

    def get_queryset(self):
        return Site.objects.moderated(self.request.user).filter(
            review_requested__isnull=False
        )


class StationListViewSet(
    DataTablesListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StationSerializer
    permission_classes = (
        IsAuthenticated,
        CanEditSite,
    )

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = StationFilter
    ordering_fields = ["name", "num_flags", "created", "last_update", "last_publish"]
    ordering = ("name",)

    def get_queryset(self):
        return (
            Site.objects.editable_by(self.request.user)
            .prefetch_related(
                "agencies", "networks", "owner__agencies", "last_user__agencies"
            )
            .select_related(
                "owner",
                "last_user",
                "review_requested",
                "updates_rejected",
                "import_alert",
            )
        )


class LogEntryViewSet(DataTablesListMixin, viewsets.GenericViewSet):
    serializer_class = LogEntrySerializer
    permission_classes = (IsAuthenticated,)

    class LogEntryFilter(CrispyFormCompat, FilterSet):
        sites = None

        def __init__(self, data=None, queryset=None, *, request=None, **kwargs):
            super().__init__(data, queryset=queryset, request=request, **kwargs)
            # we chain this filter so when someone filters the station list
            # we can show the log entries corresponding to the filtered
            # stations
            self.sites = StationFilter(
                data=data, queryset=Site.objects.all(), request=request, **kwargs
            )

        def filter_queryset(self, queryset):
            return super().filter_queryset(queryset).filter(site__in=self.sites.qs)

        site = django_filters.CharFilter(field_name="site__name", lookup_expr="iexact")
        user = django_filters.CharFilter(field_name="user__email", lookup_expr="iexact")
        before = django_filters.CharFilter(field_name="timestamp", lookup_expr="lt")
        after = django_filters.CharFilter(field_name="timestamp", lookup_expr="gte")
        ip = django_filters.CharFilter(field_name="ip", lookup_expr="iexact")

        class Meta:
            model = LogEntry
            fields = ("site", "user", "before", "after", "ip")

    filter_backends = (DjangoFilterBackend,)
    filterset_class = LogEntryFilter

    def get_queryset(self):
        return LogEntry.objects.for_user(self.request.user).select_related(
            "section", "site", "file", "user"
        )


class AlertViewSet(
    DataTablesListMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AlertSerializer
    permission_classes = (IsAuthenticated, CanDeleteAlert)

    class AlertFilter(CrispyFormCompat, FilterSet):
        sites = None

        def __init__(self, data=None, queryset=None, *, request=None, **kwargs):
            super().__init__(data, queryset=queryset, request=request, **kwargs)
            self.sites = StationFilter(
                data=data, queryset=Site.objects.all(), request=request, **kwargs
            )

        site = django_filters.CharFilter(method="for_site", distinct=True)
        user = django_filters.CharFilter(method="for_user", distinct=True)

        def filter_queryset(self, queryset):
            return (
                super()
                .filter_queryset(queryset)
                .concerning_sites(self.sites.qs)
                .distinct()
            )

        def for_site(self, queryset, name, value):
            return queryset.for_site(
                Site.objects.filter(name__iexact=value).first()
            ).distinct()

        def for_user(self, queryset, name, value):
            return queryset.for_user(
                get_user_model().filter(email__iexact=value)
            ).distinct()

        class Meta:
            model = Alert
            fields = (
                "site",
                "user",
            )
            distinct = True

    filter_backends = (DjangoFilterBackend,)
    filterset_class = AlertFilter

    def get_queryset(self):
        Alert.objects.delete_expired()
        return Alert.objects.visible_to(self.request.user)


class UserProfileViewSet(
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserSerializer
    permission_classes = (
        IsAuthenticated,
        IsUserOrAdmin,
    )
    parser_classes = (FormParser, JSONParser)

    def get_queryset(self):
        return (
            get_user_model()
            .objects.filter(id=self.request.user.id)
            .select_related("profile")
            .prefetch_related("agencies")
        )

    def list(self, request, **kwargs):
        resp = super(UserProfileViewSet, self).list(request, **kwargs)
        resp.data = resp.data[0]
        return resp

    def update(self, request, *args, **kwargs):
        from django.contrib import messages

        resp = super().update(request, *args, **kwargs)
        if resp.status_code < 300:
            messages.add_message(
                request, messages.SUCCESS, _("User profile updated successfully.")
            )
        return resp


class SiteLogDownloadViewSet(BaseSiteLogDownloadViewSet):
    class ArchiveIndexFilter(BaseSiteLogDownloadViewSet.ArchiveIndexFilter):
        unpublished = SLMBooleanFilter(method="noop")
        unpublished.help = _(
            "If true, download the published version of the log. If false,"
            "the HEAD version of the log "
        )

        class Meta(BaseSiteLogDownloadViewSet.ArchiveIndexFilter.Meta):
            fields = (
                "unpublished",
                *BaseSiteLogDownloadViewSet.ArchiveIndexFilter.Meta.fields,
            )

    filterset_class = ArchiveIndexFilter

    def retrieve(self, request, *args, **kwargs):
        if request.GET.get("unpublished", False):
            try:
                site = Site.objects.get(name__iexact=kwargs.get("site"))
                return FileResponse(
                    BytesIO(
                        SiteLogSerializer(instance=site, published=None)
                        .format(request.accepted_renderer.format)
                        .encode()
                    ),
                    filename=site.get_filename(
                        log_format=request.accepted_renderer.format,
                        epoch=datetime.now(),
                        name_len=request.GET.get("name_len", None),
                        lower_case=request.GET.get("lower_case", False),
                    ),
                )
            except Site.DoesNotExist:
                raise Http404()
        return super().retrieve(request, *args, **kwargs)


class SectionViewSet(type):
    """
    POST, PUT and PATCH all behave the same way for the section edit API.

    Each runs through the following steps:

    1) Permission check - only moderators are permitted to submit _flags or
        publish=True
    """

    def __new__(metacls, name, bases, namespace, **kwargs):
        ModelClass = kwargs.pop("model")
        can_delete = issubclass(ModelClass, SiteSubSection)
        parents = [
            *bases,
            mixins.RetrieveModelMixin,
            mixins.ListModelMixin,
            mixins.UpdateModelMixin,
            mixins.CreateModelMixin,
        ]
        if can_delete:
            parents.append(mixins.DestroyModelMixin)

        parents.append(viewsets.GenericViewSet)
        obj = super().__new__(metacls, name, tuple(parents), namespace)

        class ViewSetFilter(CrispyFormCompat, FilterSet):
            site = django_filters.CharFilter(
                field_name="site__name", lookup_expr="iexact"
            )

            class Meta:
                model = ModelClass
                fields = ["site", "id"] + (
                    ["subsection"] if issubclass(ModelClass, SiteSubSection) else []
                )

        class ViewSetSerializer(ModelSerializer):
            def build_standard_field(self, field_name, model_field):
                """
                Force EnumFields into django_enum's enum field type.
                """
                if model_field.__class__ in {
                    EnumIntegerField,
                    EnumPositiveIntegerField,
                    EnumBigIntegerField,
                    EnumPositiveSmallIntegerField,
                    EnumPositiveBigIntegerField,
                    EnumSmallIntegerField,
                    EnumCharField,
                }:
                    return EnumField, {
                        **super().build_standard_field(field_name, model_field)[1],
                        "enum": model_field.enum,
                        "strict": model_field.strict,
                    }
                return super().build_standard_field(field_name, model_field)

            serializer_field_mapping = {
                **ModelSerializer.serializer_field_mapping,
                models.DateTimeField: SLMDateTimeField,
                gis_models.PointField: SLMPointField,
            }

            _diff = serializers.SerializerMethodField(read_only=True)
            _flags = serializers.JSONField(
                read_only=False,
                required=False,
                encoder=SiteSection._meta.get_field("_flags").encoder,
                decoder=SiteSection._meta.get_field("_flags").decoder,
            )

            can_publish = serializers.SerializerMethodField(read_only=True)

            publish = serializers.BooleanField(write_only=True, required=False)
            revert = serializers.BooleanField(write_only=True, required=False)

            def to_internal_value(self, data):
                """
                Swap empty string for None in post data for any field that
                allows null. (You'd think this wouldn't be necessary or that
                DRF would have some kind of switch?)

                :param data:
                :return:
                """
                data = data.copy()
                for field, value in data.items():
                    if value == "" and getattr(
                        self.fields.get(field, None), "allow_null", False
                    ):
                        data[field] = None

                # if these are set to None - validation rejects them
                # todo anything else like this?
                if data.get("id", False) in {None, ""}:
                    del data["id"]

                if data.get("subsection", False) in {None, ""}:
                    del data["subsection"]

                return super().to_internal_value(data)

            def get_can_publish(self, obj):
                if "request" in self.context:
                    return self.context["request"].user.is_moderator()
                return None

            def get__diff(self, obj):
                return obj.published_diff()

            def perform_section_update(self, validated_data, instance=None):
                """
                We perform the same update routines on either a PUT, PATCH or
                POST for uniformity and convenience. This could include:

                    1. Field Update
                        * If current instance is published and this contains
                        edits create a new db row
                        * If current instance is not published update instance
                        * Issue section edited event.
                    2. New Section
                        * Issue section added event.
                    3. Flag Update
                        * Issue fields_flagged or flags_cleared event.
                    4. Publish
                        * Delete the previously published instance and set
                        instance (old or added) to published and issue
                        site_published event.
                    5. Any combination of 1, 2, 3 and 4

                :param validated_data: The validated POST data
                :param instance: The instance if this was a PUT or PATCH. POST
                    behaves the same way - so we also resolve the instance from
                    POST data if the update url was not used.
                :return:
                """
                with transaction.atomic():
                    # permission check - we do this here because operating
                    # directly on POST data in a Permission object is more
                    # difficult
                    site = validated_data.get("site") or instance.site
                    is_moderator = site.is_moderator(self.context["request"].user)
                    do_publish = validated_data.pop("publish", False)
                    do_revert = validated_data.pop("revert", False)
                    update_status = None

                    # the upload viewsets tag the context so we can tweak behavior for
                    # uploaded files
                    is_from_upload = self.context.get("upload", False)

                    if not is_moderator:
                        # non-moderators are not allowed to publish!
                        if do_publish:
                            raise PermissionDenied(
                                _(
                                    "You must have moderator privileges to "
                                    "publish site log edits."
                                )
                            )

                        # we don't disallow an accompanying edit with _flags -
                        # we just strip them out of the user doesnt have
                        # permission to add them
                        validated_data.pop("_flags", None)

                    section_id = validated_data.pop("id", None)
                    subsection = validated_data.get("subsection", None)

                    line_filter = Q(site=site)
                    if subsection is not None:
                        line_filter &= Q(subsection=subsection)

                    # get the previous section instance - if it exists
                    if instance is None:
                        # this is either a section where only one can exist or
                        # a subsection where multiple can exist
                        if not self.allow_multiple():
                            instance = (
                                ModelClass.objects.filter(site=site)
                                .order_by("-edited")
                                .select_for_update()
                                .first()
                            )
                        # this is a subsection - if the subsection IDs are not
                        # present it is
                        elif subsection is not None:
                            instance = (
                                ModelClass.objects.filter(line_filter)
                                .order_by("-edited")
                                .select_for_update()
                                .first()
                            )
                    else:
                        instance = (
                            ModelClass.objects.filter(pk=instance.pk)
                            .select_for_update()
                            .first()
                        )

                    if do_revert and instance:
                        if instance.revert():
                            reverted_to = ModelClass.objects.filter(
                                line_filter & Q(published=True)
                            ).first()
                            if reverted_to:
                                return reverted_to
                        self.context[
                            "request"
                        ]._response_status = status.HTTP_204_NO_CONTENT
                        return instance

                    try:
                        location_updated = False
                        if ModelClass is SiteLocation and not is_from_upload:
                            # if XYZ or LLH should be computed from the other we do that here, so it happens
                            # before the validators run. We also do it in save().
                            llh = validated_data.get("llh", None)
                            xyz = validated_data.get("xyz", None)

                            if (
                                ModelClass.coordinate_mode == CoordinateMode.ECEF
                                and xyz
                            ):
                                location_updated = True
                                validated_data["llh"] = Point(*xyz2llh(xyz))
                            elif (
                                ModelClass.coordinate_mode == CoordinateMode.LLH and llh
                            ):
                                location_updated = True
                                validated_data["xyz"] = Point(*llh2xyz(llh))

                        # this is a new section
                        if instance is None:
                            new_section = super().create(validated_data)
                            new_section.full_clean()
                            new_section.save()
                            update_status = new_section.edited
                            if not isinstance(new_section, SiteForm):
                                form = new_section.site.siteform_set.head()
                                if form is None:
                                    form = SiteForm.objects.create(
                                        site=site, published=False, report_type="NEW"
                                    )
                                elif form.published:
                                    form.pk = None
                                    form.published = False
                                if self.context["request"].user.full_name:
                                    form.prepared_by = self.context[
                                        "request"
                                    ].user.full_name
                                form.save()
                            slm_signals.section_added.send(
                                sender=self,
                                site=site,
                                user=self.context["request"].user,
                                request=self.context["request"],
                                timestamp=update_status,
                                section=new_section,
                            )
                            instance = new_section
                        else:
                            # if an object id was present and it is not at or past
                            # the last section ID - we have a concurrent edit race
                            # condition between one or more users.
                            if section_id is not None and section_id < instance.id:
                                raise DRFValidationError(
                                    _(
                                        "Edits must be made on HEAD. Someone else "
                                        "may be editing the log concurrently. "
                                        "Refresh and try again."
                                    )
                                )

                        # if not new - does this section have edits?
                        update = False
                        flags = validated_data.get("_flags", instance._flags)
                        edited_fields = []

                        # todo this diffing code is getting a bit messy because
                        #   of all the special type cases - consider a refactor
                        #   also needs to be DRYed w/ published_diff function
                        for field in ModelClass.site_log_fields():
                            if field in validated_data:
                                mdl_field = instance._meta.get_field(field)
                                is_many = isinstance(mdl_field, models.ManyToManyField)
                                new_value = validated_data.get(field)
                                if new_value is None and not mdl_field.null:
                                    # convert Nones to empty strings if warranted
                                    new_value = mdl_field.default
                                old_value = getattr(instance, field)
                                if (
                                    not is_many
                                    and (
                                        getattr(new_value, "coords", None)
                                        != getattr(old_value, "coords", None)
                                        if isinstance(new_value, Point)
                                        else new_value != old_value
                                    )
                                ) or (
                                    is_many
                                    and set(new_value)
                                    != set(getattr(instance, field).all())
                                ):
                                    update = True
                                    if not instance.published:
                                        edited_fields.append(field)
                                        if is_many:
                                            if new_value:
                                                getattr(instance, field).set(new_value)
                                            else:
                                                getattr(instance, field).clear()
                                        else:
                                            setattr(instance, field, new_value)

                                    # handle special case where llh/xyz are linked and if one is
                                    # updated we should remove flags for both
                                    # TODO less hard coded way to handle this -
                                    # linked fields definitions on the validators?
                                    if location_updated and field in {"llh", "xyz"}:
                                        for cfield in ["llh", "xyz"]:
                                            if cfield in flags:
                                                del flags[cfield]

                                    elif field in flags:
                                        del flags[field]

                        if update:
                            if instance.published:
                                validated_data["_flags"] = flags
                                instance.pk = None  # copy the instance
                                instance.published = False
                                instance.save()
                                for param, value in validated_data.items():
                                    if isinstance(
                                        instance._meta.get_field(param),
                                        models.ManyToManyField,
                                    ):
                                        if value:
                                            getattr(instance, param).set(value)
                                        else:
                                            getattr(instance, param).clear()
                                    else:
                                        setattr(instance, param, value)
                                instance.full_clean()
                                instance.save()
                            else:
                                instance._flags = flags
                                instance.full_clean()
                                instance.save()

                            # make sure we use edit timestamp if publish and
                            # edit are simultaneous
                            update_status = instance.edited
                            if not isinstance(instance, SiteForm):
                                form = instance.site.siteform_set.head()
                                if form.published:
                                    form.pk = None
                                    form.published = False
                                if self.context["request"].user.full_name:
                                    form.prepared_by = self.context[
                                        "request"
                                    ].user.full_name
                                form.save()
                            slm_signals.section_edited.send(
                                sender=self,
                                site=site,
                                user=self.context["request"].user,
                                request=self.context["request"],
                                timestamp=update_status,
                                section=instance,
                                fields=edited_fields,
                            )
                        elif "_flags" in validated_data:
                            # this is just a flag update
                            added = len(flags) - (
                                len(instance._flags) if instance._flags else 0
                            )
                            site.num_flags += added
                            if site.num_flags < 0:
                                site.num_flags = 0

                            site.save()
                            instance._flags = flags
                            instance.save()

                        if do_publish:
                            update_status = update_status or now()
                            if not isinstance(instance, SiteForm):
                                form = instance.site.siteform_set.head()
                                if form.published:
                                    form.pk = None
                                    form.published = False
                                    if self.context["request"].user.full_name:
                                        form.prepared_by = self.context[
                                            "request"
                                        ].user.full_name
                                form.save(modified_section=instance.dot_index)
                                form.publish(
                                    request=self.context.get("request", None),
                                    silent=True,
                                    timestamp=update_status,
                                    update_site=False,
                                )
                            instance.publish(
                                request=self.context.get("request", None),
                                timestamp=update_status,
                                update_site=False,  # this is done below
                            )
                            try:
                                instance.refresh_from_db()
                            except instance.DoesNotExist:
                                # hacky but it works, not really another way
                                # to pass information up and down the chain
                                # from serializer to view - probably means a
                                # lot of this logic belongs in the view
                                self.context[
                                    "request"
                                ]._response_status = status.HTTP_204_NO_CONTENT

                        if update_status:
                            site.update_status(
                                save=True,
                                user=self.context["request"].user,
                                timestamp=update_status,
                            )
                        return instance
                    except DjangoValidationError as ve:
                        raise DRFValidationError(ve.message_dict)

            def update(self, instance, validated_data):
                return self.perform_section_update(
                    validated_data=validated_data, instance=instance
                )

            def create(self, validated_data):
                return self.perform_section_update(validated_data=validated_data)

            @classmethod
            def allow_multiple(cls):
                """
                Does this serializer allow multiple sections per site?
                :return: True if multiple sections are allowed - False
                    otherwise
                """
                return issubclass(ModelClass, SiteSubSection)

            def build_relational_field(self, field_name, relation_info):
                """
                By default DRF will use PrimaryKeyRelatedFields to represent
                ForeignKey relations - for certain fields in the API we'd
                rather tie them based on a string field on the related model.
                If API_RELATED_FIELD is set to that field on a related model
                we use a SlugRelatedField instead so instead of passing PKs
                in the API, users can pass human readable names instead and do
                not have to do the work to figure out what the primary key is
                under the covers - as this is SLM database instance specific.

                This is also critical for our autocomplete fields.
                """
                related = getattr(
                    relation_info.related_model, "API_RELATED_FIELD", None
                )
                _, defaults = super().build_relational_field(field_name, relation_info)
                if related:
                    return (SlugRelatedField, {**defaults, "slug_field": related})
                return _, defaults

            class Meta:
                model = ModelClass

                # prevent UniqueTogetherValidator from being attached
                # subsection and section ids are attached after the data
                # validation process and uniqueness qualities are enforced
                # by the code, it should be impossible for a user to use the
                # api in a way that would trigger the database to violate
                # this constraint
                validators = []

                fields = [
                    "site",
                    "id",
                    "publish",
                    "published",
                    "revert",
                    "can_publish",
                    "_flags",
                    "_diff",
                    *ModelClass.site_log_fields(),
                ] + (
                    ["subsection", "heading", "effective", "is_deleted"]
                    if issubclass(ModelClass, SiteSubSection)
                    else []
                )

                extra_kwargs = {
                    "id": {"required": False, "read_only": False},
                    "site": {"required": True},
                    **(
                        {
                            "heading": {"required": False, "read_only": True},
                            "effective": {"required": False, "read_only": True},
                            "is_deleted": {"required": False, "read_only": True},
                            "subsection": {"required": False},
                            "four_character_id": {  # special case
                                "required": False,
                                "read_only": True,
                            },
                            "nine_character_id": {  # special case
                                "required": False,
                                "read_only": True,
                            },
                            "custom_graphic": {"trim_whitespace": False},
                        }
                        if issubclass(ModelClass, SiteSubSection)
                        else {}
                    ),
                }

        obj.serializer_class = ViewSetSerializer
        obj.filterset_class = ViewSetFilter
        obj.permission_classes = (IsAuthenticated, CanEditSite, VerifyModerationActions)
        obj.pagination_class = DataTablesPagination
        obj.filter_backends = (DjangoFilterBackend,)

        def get_queryset(self):
            return ModelClass.objects.editable_by(self.request.user).select_related(
                "site"
            )

        def create(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                self.perform_create(serializer)
            except DjangoValidationError as ve:
                raise DRFValidationError(ve.message_dict)

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=getattr(request, "_response_status", status.HTTP_201_CREATED),
                headers=headers,
            )

        def update(self, request, *args, **kwargs):
            response = mixins.UpdateModelMixin.update(self, request, *args, **kwargs)
            response.status_code = getattr(
                request, "_response_status", response.status_code
            )
            return response

        def destroy(self, request, *args, **kwargs):
            instance = self.get_object()
            instance = self.perform_destroy(instance)
            if instance:
                serializer = self.get_serializer(instance=instance)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data,
                    status=getattr(request, "_response_status", status.HTTP_200_OK),
                    headers=headers,
                )
            return Response(
                status=getattr(request, "_response_status", status.HTTP_204_NO_CONTENT)
            )

        def perform_destroy(self, instance):
            """
            Deletes must happen on head:

            1) If head is published, the delete flag will be marked
            2) If head is unpublished, but no previously published section
                exists the record will be deleted.
            3) If head is unpublished, but previous published sections exist,
                the unpublished record will be deleted and the published record
                will have its is_deleted flag set.

            Sections are fully deleted when a published record with the
            is_deleted flag set is published.

            :param self: view class instance
            :param instance: The section or subsection instance
            """
            with transaction.atomic():
                section = ModelClass.objects.select_for_update().get(pk=instance.pk)
                site = section.site
                published = ModelClass.objects.filter(
                    site=section.site, subsection=section.subsection, published=True
                ).first()

                if not section.published:
                    # we delete it if this section or subsection has never
                    # been published before
                    section.delete()

                if published:
                    published.is_deleted = True
                    published.save()
                    form = section.site.siteform_set.head()
                    if form.published:
                        form.pk = None
                        form.published = False
                    if self.request.user.full_name:
                        form.prepared_by = self.request.user.full_name
                    form.save()
                    to_return = published
                else:
                    to_return = None

                slm_signals.section_deleted.send(
                    sender=self,
                    site=site,
                    user=self.request.user,
                    request=self.request,
                    timestamp=now(),
                    section=section,
                )

                site.update_status(save=True, user=self.request.user, timestamp=now())
                return to_return

        obj.get_queryset = get_queryset
        if can_delete:
            obj.perform_destroy = perform_destroy
            obj.destroy = destroy
        obj.create = create
        obj.update = update
        return obj


# TODO all these can be constructed dynamically from the models
class SiteFormViewSet(metaclass=SectionViewSet, model=SiteForm):
    pass


class SiteIdentificationViewSet(metaclass=SectionViewSet, model=SiteIdentification):
    pass


class SiteLocationViewSet(metaclass=SectionViewSet, model=SiteLocation):
    pass


class SiteReceiverViewSet(metaclass=SectionViewSet, model=SiteReceiver):
    pass


class SiteAntennaViewSet(metaclass=SectionViewSet, model=SiteAntenna):
    pass


class SiteSurveyedLocalTiesViewSet(
    metaclass=SectionViewSet, model=SiteSurveyedLocalTies
):
    pass


class SiteFrequencyStandardViewSet(
    metaclass=SectionViewSet, model=SiteFrequencyStandard
):
    pass


class SiteCollocationViewSet(metaclass=SectionViewSet, model=SiteCollocation):
    pass


class SiteHumiditySensorViewSet(metaclass=SectionViewSet, model=SiteHumiditySensor):
    pass


class SitePressureSensorViewSet(metaclass=SectionViewSet, model=SitePressureSensor):
    pass


class SiteTemperatureSensorViewSet(
    metaclass=SectionViewSet, model=SiteTemperatureSensor
):
    pass


class SiteWaterVaporRadiometerViewSet(
    metaclass=SectionViewSet, model=SiteWaterVaporRadiometer
):
    pass


class SiteOtherInstrumentationViewSet(
    metaclass=SectionViewSet, model=SiteOtherInstrumentation
):
    pass


class SiteRadioInterferencesViewSet(
    metaclass=SectionViewSet, model=SiteRadioInterferences
):
    pass


class SiteMultiPathSourcesViewSet(metaclass=SectionViewSet, model=SiteMultiPathSources):
    pass


class SiteSignalObstructionsViewSet(
    metaclass=SectionViewSet, model=SiteSignalObstructions
):
    pass


class SiteLocalEpisodicEffectsViewSet(
    metaclass=SectionViewSet, model=SiteLocalEpisodicEffects
):
    pass


class SiteOperationalContactViewSet(
    metaclass=SectionViewSet, model=SiteOperationalContact
):
    pass


class SiteResponsibleAgencyViewSet(
    metaclass=SectionViewSet, model=SiteResponsibleAgency
):
    pass


class SiteMoreInformationViewSet(metaclass=SectionViewSet, model=SiteMoreInformation):
    pass


class SiteFileUploadViewSet(
    DataTablesListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    logger = getLogger("slm.api.edit.views.SiteFileUploadViewSet")

    serializer_class = SiteFileUploadSerializer
    permission_classes = (
        IsAuthenticated,
        CanEditSite,
    )
    parser_classes = (MultiPartParser, FormParser, JSONParser, FileUploadParser)

    site = None

    SECTION_VIEWS = {
        0: SiteFormViewSet,
        1: SiteIdentificationViewSet,
        2: SiteLocationViewSet,
        3: SiteReceiverViewSet,
        4: SiteAntennaViewSet,
        5: SiteSurveyedLocalTiesViewSet,
        6: SiteFrequencyStandardViewSet,
        7: SiteCollocationViewSet,
        (8, 1): SiteHumiditySensorViewSet,
        (8, 2): SitePressureSensorViewSet,
        (8, 3): SiteTemperatureSensorViewSet,
        (8, 4): SiteWaterVaporRadiometerViewSet,
        (8, 5): SiteOtherInstrumentationViewSet,
        (9, 1): SiteRadioInterferencesViewSet,
        (9, 2): SiteMultiPathSourcesViewSet,
        (9, 3): SiteSignalObstructionsViewSet,
        10: SiteLocalEpisodicEffectsViewSet,
        11: SiteOperationalContactViewSet,
        12: SiteResponsibleAgencyViewSet,
        13: SiteMoreInformationViewSet,
    }

    @staticmethod
    def get_subsection_id(section):
        if section.section_number in {3, 4, 5, 6, 7, 8, 9, 10}:
            return section.ordering_id
        return None

    class FileFilter(CrispyFormCompat, AcceptListArguments, FilterSet):
        name = django_filters.CharFilter(field_name="name", lookup_expr="istartswith")

        file_type = django_filters.MultipleChoiceFilter(choices=SLMFileType.choices)

        log_format = django_filters.MultipleChoiceFilter(choices=SiteLogFormat.choices)

        status = django_filters.MultipleChoiceFilter(
            choices=SiteFileUploadStatus.choices
        )

        class Meta:
            model = SiteFileUpload
            fields = ("name", "status", "file_type", "log_format")

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = FileFilter
    ordering_fields = ["-timestamp", "name"]

    original_request = None

    def dispatch(self, request, *args, **kwargs):
        self.site = kwargs.pop("site", None)
        self.original_request = request
        try:
            self.site = Site.objects.get(name__iexact=self.site)
        except Site.DoesNotExist:
            return HttpResponseNotFound(f"{self.site} does not exist.")

        if not self.site.can_edit(request.user):
            return HttpResponseForbidden(
                f"{request.user} cannot edit site {self.site.name}"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return SiteFileUpload.objects.available_to(self.request.user).filter(
            site=self.site
        )

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        if instance.file_type is not SLMFileType.SITE_LOG:
            slm_signals.site_file_deleted.send(
                sender=self,
                site=self.site,
                user=self.original_request.user,
                timestamp=now(),
                request=self.original_request,
                upload=instance,
            )

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            if "file" not in request.FILES:
                return Response("Expected a file upload with name 'file'.", status=400)

            upload = SiteFileUpload(
                site=self.site,
                file=request.FILES["file"],
                name=request.FILES["file"].name[:255],
                mimetype=request.FILES["file"].content_type,
                user=request.user,
            )
            upload.save()
            slm_signals.site_file_uploaded.send(
                sender=self,
                site=self.site,
                user=request.user,
                timestamp=upload.timestamp,
                request=request,
                upload=upload,
            )

            if upload.file_type is SLMFileType.SITE_LOG:
                from slm.parsing.legacy import SiteLogBinder, SiteLogParser

                if upload.log_format in [
                    SiteLogFormat.LEGACY,
                    SiteLogFormat.ASCII_9CHAR,
                ]:
                    with upload.file.open() as uplf:
                        content = uplf.read()
                        encoding = detect(content).get("encoding", "utf-8")
                        try:
                            bound_log = SiteLogBinder(
                                SiteLogParser(
                                    content.decode(encoding), site_name=self.site.name
                                )
                            ).parsed
                        except (UnicodeDecodeError, LookupError):
                            upload.status = SiteFileUploadStatus.INVALID
                            upload.save()
                            return Response(
                                {
                                    "file": upload.id,
                                    "error": _(
                                        "Unable to decode this text file - please "
                                        "ensure the file is encoded in UTF-8 and "
                                        "try again."
                                    ),
                                },
                                status=400,
                            )
                        if not bound_log.errors:
                            self.update_from_legacy(request, bound_log)

                        upload.context = bound_log.context
                        if bound_log.errors:
                            upload.status = SiteFileUploadStatus.INVALID
                            upload.save()
                            return Response(
                                {
                                    "file": upload.id,
                                    "error": _(
                                        "There were errors parsing the site log."
                                    ),
                                },
                                status=400,
                            )
                        upload.status = (
                            SiteFileUploadStatus.WARNINGS
                            if bound_log.warnings
                            else SiteFileUploadStatus.VALID
                        )
                        upload.save()

                elif upload.log_format is SiteLogFormat.GEODESY_ML:
                    from slm.parsing.xsd import SiteLogBinder, SiteLogParser

                    with upload.file.open() as uplf:
                        content = uplf.read()
                        encoding = detect(content).get("encoding", "utf-8")
                        try:
                            parsed = SiteLogParser(
                                content.decode(encoding), site_name=self.site.name
                            )
                        except (UnicodeDecodeError, LookupError):
                            upload.status = SiteFileUploadStatus.INVALID
                            upload.save()
                            return Response(
                                {
                                    "file": upload.id,
                                    "error": _(
                                        "Unable to decode this xml file - please "
                                        "ensure the file is encoded in UTF-8 and "
                                        "try again."
                                    ),
                                },
                                status=400,
                            )

                        upload.context = parsed.context
                        if parsed.errors:
                            upload.status = SiteFileUploadStatus.INVALID
                            upload.save()
                            return Response(
                                {
                                    "file": upload.id,
                                    "error": _(
                                        "There were errors parsing the site log."
                                    ),
                                },
                                status=400,
                            )
                        upload.save()
                        return Response(
                            "GeodesyML uploads are not yet supported.", status=400
                        )

                elif upload.log_format is SiteLogFormat.JSON:
                    return Response("JSON uploads are not yet supported.", status=400)
                else:
                    return Response("Unsupported site log upload format.", status=400)
            elif upload.file_type is SLMFileType.SITE_IMAGE:
                # automagically set the view direction if its specified on
                # the filename
                if upload.direction is None:
                    lower_name = upload.name.lower()
                    if "north" in lower_name:
                        upload.direction = CardinalDirection.NORTH
                        if "east" in lower_name:
                            upload.direction = CardinalDirection.NORTH_EAST
                        elif "west" in lower_name:
                            upload.direction = CardinalDirection.NORTH_WEST
                        upload.save()
                    elif "south" in lower_name:
                        upload.direction = CardinalDirection.SOUTH
                        if "east" in lower_name:
                            upload.direction = CardinalDirection.SOUTH_EAST
                        elif "west" in lower_name:
                            upload.direction = CardinalDirection.SOUTH_WEST
                        upload.save()
                    elif "east" in lower_name:
                        upload.direction = CardinalDirection.EAST
                        upload.save()
                    elif "west" in lower_name:
                        upload.direction = CardinalDirection.WEST
                        upload.save()

        upload.site.synchronize()
        return Response(self.get_serializer(instance=upload).data, status=200)

    def perform_update(self, serializer):
        # do permissions check on publish/unpublish action - also only allow
        # a subset of status changes
        if (
            serializer.validated_data.get("status", None) is not None
            and serializer.validated_data["status"] != serializer.instance.status
            and not self.site.is_moderator(self.request.user)
        ):
            raise PermissionDenied("Must be a moderator to publish site files.")
        if serializer.validated_data.get("status", None) and (
            SiteFileUploadStatus(serializer.validated_data["status"])
            not in {SiteFileUploadStatus.PUBLISHED, SiteFileUploadStatus.UNPUBLISHED}
        ):
            raise PermissionDenied("Files may only be published or unpublished.")
        status = serializer.instance.status
        super().perform_update(serializer)

        if (status, serializer.instance.status) == (
            SiteFileUploadStatus.UNPUBLISHED,
            SiteFileUploadStatus.PUBLISHED,
        ):
            slm_signals.site_file_published.send(
                sender=self,
                site=self.site,
                user=self.original_request.user,
                timestamp=now(),
                request=self.original_request,
                upload=serializer.instance,
            )
        elif (status, serializer.instance.status) == (
            SiteFileUploadStatus.PUBLISHED,
            SiteFileUploadStatus.UNPUBLISHED,
        ):
            slm_signals.site_file_unpublished.send(
                sender=self,
                site=self.site,
                user=self.original_request.user,
                timestamp=now(),
                request=self.original_request,
                upload=serializer.instance,
            )
        self.site.synchronize()

    def update_from_legacy(self, request, parsed):
        errors = {}

        existing_sections = {}
        posted_subsections = {
            3: set(),
            4: set(),
            5: set(),
            6: set(),
            7: set(),
            (8, 1): set(),
            (8, 2): set(),
            (8, 3): set(),
            (8, 4): set(),
            (8, 5): set(),
            (9, 1): set(),
            (9, 2): set(),
            (9, 3): set(),
            10: set(),
        }
        with transaction.atomic():
            # we reverse this so we process the form section last which will
            # ensure that the prepared by field will be set to what was given
            # in the upload log
            for index, section in reversed(parsed.sections.items()):
                if section.example:
                    continue
                section_view = self.SECTION_VIEWS.get(section.heading_index, None)
                # this is a complicated conditional to determine if the section is a subsection
                # header with no bindable values - think about encapsulating this logic onto
                # the binder
                if (
                    section_view
                    and issubclass(
                        section_view.serializer_class.Meta.model, SiteSubSection
                    )
                    and not isinstance(section.order, int)
                    and not section.contains_values
                ):
                    # skip subsection headers
                    continue
                if section_view:
                    data = {**(section.binding or {}), "site": self.site.id}
                    subsection_number = self.get_subsection_id(section)
                    if subsection_number is not None:
                        # we have to find the right subsection identifiers
                        # (which don't necessarily equal the existing ids)
                        if section.heading_index not in existing_sections:
                            existing_sections[section.heading_index] = list(
                                section_view.serializer_class.Meta.model.objects.filter(
                                    site=self.site, is_deleted=False
                                )
                                .head()
                                .sort()
                            )
                        if (
                            len(existing_sections[section.heading_index])
                            > subsection_number - 1
                        ):
                            instance = existing_sections[section.heading_index][
                                subsection_number - 1
                            ]
                            data["subsection"] = instance.subsection
                            posted_subsections[section.heading_index].add(instance)

                    serializer = section_view.serializer_class(
                        data=data, context={"request": request, "upload": True}
                    )
                    if not serializer.is_valid(raise_exception=False):
                        errors[index] = {
                            param: "\n".join([str(detail) for detail in details])
                            for param, details in serializer.errors.items()
                        }
                    else:
                        try:
                            serializer.save()
                            for param, flag in serializer.instance._flags.items():
                                params = section.get_params(param)
                                for parsed_param in params:
                                    for line_no in range(
                                        parsed_param.line_no, parsed_param.line_end + 1
                                    ):
                                        parsed.add_finding(
                                            Warn(
                                                line_no,
                                                parsed,
                                                str(flag),
                                                section=section,
                                            )
                                        )
                        except (DjangoValidationError, DRFValidationError) as dve:
                            for param, error_list in getattr(
                                dve, "message_dict", getattr(dve, "detail")
                            ).items():
                                errors.setdefault(index, {})[param] = "\n".join(
                                    [str(msg) for msg in error_list]
                                )

            if errors:
                # if any section fails - rollback all sections
                transaction.set_rollback(True)
                for section_index, section_errors in errors.items():
                    for param, error in section_errors.items():
                        section = parsed.sections[section_index]
                        params = section.get_params(param)
                        if params:
                            for parsed_param in params:
                                for line_no in range(
                                    parsed_param.line_no, parsed_param.line_end + 1
                                ):
                                    parsed.add_finding(
                                        Error(
                                            line_no, parsed, str(error), section=section
                                        )
                                    )
                        else:
                            parsed.add_finding(
                                Error(
                                    section.line_no, parsed, str(error), section=section
                                )
                            )
                return errors

        # delete any subsections that are current but not present in the
        # uploaded sitelog
        for heading_index, existing in existing_sections.items():
            section_view = self.SECTION_VIEWS.get(heading_index, None)
            if section_view:
                for instance in set(existing).difference(
                    posted_subsections.get(heading_index, set())
                ):
                    view = section_view()
                    view.request = request
                    try:
                        view.perform_destroy(instance)
                    except Exception:
                        # catch everything here - if this does not happen
                        # its not the end of the world - the exception log
                        # will notify the relevant parties that there's some
                        # kind of issue
                        self.logger.exception(
                            "Error deleting subsection %d of section %s",
                            instance.subsection,
                            heading_index,
                        )
        return errors

    def retrieve(self, request, *args, **kwargs):
        """
        By default the edit api GET will return a json structure with
        information about the file. Adding ?download to the url will download
        the file itself.
        """
        if request.GET.get("download", None) is None:
            return super().retrieve(request, *args, **kwargs)

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


class ImageOperationsViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, CanEditSite)

    def get_queryset(self):
        return SiteFileUpload.objects.filter(file_type=SLMFileType.SITE_IMAGE)

    def retrieve(self, request, *args, **kwargs):
        rotate = request.GET.get("rotate", None)
        try:
            if rotate:
                file = self.get_object()
                file.rotate(int(rotate))
        except ValueError:
            return Response({"rotate": "rotate must be an integer"}, status=400)
        return Response(status=204)
