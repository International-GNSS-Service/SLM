from logging import getLogger

from io import BytesIO
import django_filters
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.http.response import (
    HttpResponseForbidden,
    HttpResponseNotFound,
    FileResponse
)
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import mixins, renderers, serializers, status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.serializers import SlugRelatedField
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import (
    FileUploadParser,
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from slm import signals as slm_signals
from slm.api.filter import (
    AcceptListArguments,
    MustIncludeThese
)
from slm.api.edit.serializers import (
    AlertSerializer,
    LogEntrySerializer,
    ReviewRequestSerializer,
    SiteFileUploadSerializer,
    StationSerializer,
    UserSerializer,
)
from slm.api.public.views import (
    AgencyViewSet as PublicAgencyViewSet,
    NetworkViewSet as PublicNetworkViewSet
)
from slm.api.fields import SLMDateTimeField
from slm.api.serializers import SiteLogSerializer
from slm.api.pagination import DataTablesPagination
from slm.api.permissions import (
    CanDeleteAlert,
    CanEditSite,
    CanRejectReview,
    IsUserOrAdmin,
    UpdateAdminOnly,
)
from slm.api.views import BaseSiteLogDownloadViewSet
from slm.defines import (
    SiteFileUploadStatus,
    SiteLogFormat,
    SLMFileType,
    ISOCountry
)
from slm.parsing.legacy.parser import Error
from slm.models import (
    Alert,
    LogEntry,
    Network,
    Agency,
    Receiver,
    Antenna,
    Radome,
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
from django.utils.functional import cached_property
from django.db.models import Q, Subquery, OuterRef
from slm.defines import SiteLogStatus, AlertLevel
from slm.api.filter import SLMBooleanFilter
from django.http import Http404
from datetime import datetime


class StationFilter(AcceptListArguments, FilterSet):
    """
    Edit API station filter extensions.
    """
    @property
    def current_equipment(self):
        return self.form.cleaned_data.get('current', None)

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

    receiver = django_filters.ModelMultipleChoiceFilter(
        method='filter_receivers',
        queryset=Receiver.objects.all(),
        distinct=True
    )

    antenna = django_filters.ModelMultipleChoiceFilter(
        method='filter_antennas',
        queryset=Antenna.objects.all(),
        distinct=True
    )

    radome = django_filters.ModelMultipleChoiceFilter(
        method='filter_radomes',
        queryset=Radome.objects.all(),
        distinct=True
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

    alert_level = django_filters.MultipleChoiceFilter(
        choices=[(level.value, level.label) for level in AlertLevel],
        method='filter_alert_level'
    )

    country = django_filters.MultipleChoiceFilter(
        choices=[(country.value, country.label) for country in ISOCountry],
        field_name='sitelocation__country'
    )

    current = SLMBooleanFilter(
        method='noop',
        distinct=True,
        field_name='current'
    )

    def noop(self, queryset, name, value):
        return queryset

    def filter_alerts(self, queryset, name, value):
        alert_q = Q()
        for alert in value:
            alert_q |= Q(
                **{f'{self.alert_fields[alert.lower()]}__isnull': False}
            )
        return queryset.filter(alert_q)

    def filter_alert_level(self, queryset, name, value):
        level_q = Q()
        for alerts in Site.alert_fields:
            level_q |= Q(
                **{f'{alerts}__level__in': value}
            )
        return queryset.filter(level_q)

    def filter_receivers(self, queryset, name, value):
        if value:
            if self.current_equipment:
                latest_receiver = SiteReceiver.objects.filter(
                    Q(site=OuterRef('pk')) & Q(is_deleted=False)
                ).order_by('-edited')
                return queryset.annotate(
                    receiver=Subquery(
                        latest_receiver.values('receiver_type')[:1]
                    )).filter(receiver__in=value).distinct()
            else:
                return queryset.filter(
                    sitereceiver__receiver_type__in=value
                ).distinct()
        return queryset

    def filter_antennas(self, queryset, name, value):
        if value:
            if self.current_equipment:
                latest_antenna = SiteAntenna.objects.filter(
                    Q(site=OuterRef('pk')) & Q(is_deleted=False)
                ).order_by('-edited')
                return queryset.annotate(
                    antenna=Subquery(
                        latest_antenna.values('antenna_type')[:1])
                ).filter(antenna__in=value).distinct()
            else:
                return queryset.filter(
                    siteantenna__antenna_type__in=value
                ).distinct()
        return queryset

    def filter_radomes(self, queryset, name, value):
        if value:
            if self.current_equipment:
                latest_antenna = SiteAntenna.objects.filter(
                    Q(site=OuterRef('pk')) & Q(is_deleted=False)
                ).order_by('-edited')
                return queryset.annotate(
                    radome=Subquery(
                        latest_antenna.values('radome_type')[:1])
                ).filter(radome__in=value).distinct()
            else:
                return queryset.filter(
                    siteantenna__radome_type__in=value
                ).distinct()
        return queryset

    class Meta:
        model = Site
        fields = (
            'id',
            'name',
            'agency',
            'network',
            'receiver',
            'antenna',
            'radome',
            'country',
            'published_before',
            'published_after',
            'updated_before',
            'updated_after',
            'status',
            'alert_level',
            'current'
        )
        distinct = True


class PassThroughRenderer(renderers.BaseRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = ''
    format = 'legacy'

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
    viewsets.GenericViewSet
):
    serializer_class = ReviewRequestSerializer
    permission_classes = (IsAuthenticated, CanEditSite)

    def perform_update(self, serializer):
        slm_signals.review_requested.send(
            sender=self,
            site=serializer.instance,
            detail=serializer.validated_data.get('detail', None),
            request=self.request
        )
        serializer.instance.refresh_from_db()

    def get_queryset(self):
        return Site.objects.editable_by(
            self.request.user
        ).filter(review_requested__isnull=True).filter(
            status__in=SiteLogStatus.unpublished_states()
        ).annotate_max_alert()


class RejectUpdatesView(
    DataTablesListMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = ReviewRequestSerializer
    permission_classes = (IsAuthenticated, CanRejectReview)

    def perform_update(self, serializer):
        slm_signals.updates_rejected.send(
            sender=self,
            site=serializer.instance,
            detail=serializer.validated_data.get('detail', None),
            request=self.request
        )
        serializer.instance.refresh_from_db()

    def get_queryset(self):
        return Site.objects.moderated(
            self.request.user
        ).filter(review_requested__isnull=False).annotate_max_alert()


class StationListViewSet(
    DataTablesListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    
    serializer_class = StationSerializer
    permission_classes = (IsAuthenticated, CanEditSite,)

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = StationFilter
    ordering_fields = [
        'name',
        'num_flags',
        'created',
        'last_update',
        'last_publish'
    ]
    ordering = ('name',)

    def get_queryset(self):
        return Site.objects.editable_by(
            self.request.user
        ).prefetch_related(
            'agencies',
            'networks',
            'owner__agencies',
            'last_user__agencies'
        ).select_related(
            'owner',
            'last_user',
            'review_requested',
            'updates_rejected'
        ).annotate_max_alert()


class LogEntryViewSet(DataTablesListMixin, viewsets.GenericViewSet):

    serializer_class = LogEntrySerializer
    permission_classes = (IsAuthenticated,)

    class LogEntryFilter(FilterSet):

        sites = None

        def __init__(
            self,
            data=None,
            queryset=None,
            *,
            request=None,
            **kwargs
        ):
            super().__init__(
                data,
                queryset=queryset,
                request=request,
                **kwargs
            )
            # we chain this filter so when someone filters the station list
            # we can show the log entries corresponding to the filtered
            # stations
            self.sites = StationFilter(
                data=data,
                queryset=Site.objects.annotate_max_alert(),
                request=request,
                **kwargs
            )

        def filter_queryset(self, queryset):
            return super().filter_queryset(queryset).filter(
                site__in=self.sites.qs
            )

        site = django_filters.CharFilter(
            field_name='site__name',
            lookup_expr='iexact'
        )
        user = django_filters.CharFilter(
            field_name='user__email',
            lookup_expr='iexact'
        )
        before = django_filters.CharFilter(
            field_name='timestamp',
            lookup_expr='lt'
        )
        after = django_filters.CharFilter(
            field_name='timestamp',
            lookup_expr='gte'
        )
        ip = django_filters.CharFilter(
            field_name='ip',
            lookup_expr='iexact'
        )

        class Meta:
            model = LogEntry
            fields = ('site', 'user', 'before', 'after', 'ip')

    filter_backends = (DjangoFilterBackend,)
    filterset_class = LogEntryFilter

    def get_queryset(self):
        return LogEntry.objects.for_user(
            self.request.user
        ).prefetch_related(
            'site_log_object'
        )


class AlertViewSet(
    DataTablesListMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = AlertSerializer
    permission_classes = (IsAuthenticated, CanDeleteAlert)

    class AlertFilter(FilterSet):

        sites = None

        def __init__(
            self,
            data=None,
            queryset=None,
            *,
            request=None,
            **kwargs
        ):
            super().__init__(
                data,
                queryset=queryset,
                request=request,
                **kwargs
            )
            self.sites = StationFilter(
                data=data,
                queryset=Site.objects.annotate_max_alert(),
                request=request,
                **kwargs
            )

        site = django_filters.CharFilter(method='for_site')
        user = django_filters.CharFilter(method='for_user')

        def filter_queryset(self, queryset):
            return super().filter_queryset(queryset).concerning_sites(
                self.sites.qs
            )

        def for_site(self, queryset, name, value):
            return queryset.for_site(
                Site.objects.filter(name__iexact=value).first()
            )

        def for_user(self, queryset, name, value):
            return queryset.for_user(
                get_user_model().filter(email__iexact=value)
            )

        class Meta:
            model = Alert
            fields = ('site', 'user',)

    filter_backends = (DjangoFilterBackend,)
    filterset_class = AlertFilter

    def get_queryset(self):
        Alert.objects.delete_expired()
        return Alert.objects.visible_to(self.request.user)


class UserProfileViewSet(
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, IsUserOrAdmin,)
    parser_classes = (FormParser, JSONParser)

    def get_queryset(self):
        return get_user_model().objects.filter(
            id=self.request.user.id
        ).select_related('profile').prefetch_related('agencies')

    def list(self, request, **kwargs):
        resp = super(UserProfileViewSet, self).list(request, **kwargs)
        resp.data = resp.data[0]
        return resp

    def update(self, request, *args, **kwargs):
        from django.contrib import messages
        resp = super().update(request, *args, **kwargs)
        if resp.status_code < 300:
            messages.add_message(
                request,
                messages.SUCCESS,
                _('User profile updated successfully.')
            )
        return resp


class SiteLogDownloadViewSet(BaseSiteLogDownloadViewSet):

    class SiteIndexFilter(BaseSiteLogDownloadViewSet.SiteIndexFilter):

        unpublished = SLMBooleanFilter(method='get_unpublished')
        unpublished.help = _(
            'If true, download the published version of the log. If false,'
            'the HEAD version of the log '
        )

        def get_unpublished(self, queryset, **_):
            return queryset.none()

        class Meta(BaseSiteLogDownloadViewSet.SiteIndexFilter.Meta):
            fields = (
                'unpublished',
                *BaseSiteLogDownloadViewSet.SiteIndexFilter.Meta.fields
            )

    filterset_class = SiteIndexFilter

    def retrieve(self, request, *args, **kwargs):
        if request.GET.get('unpublished', False):
            try:
                site = Site.objects.get(name__iexact=kwargs.get('site'))
                return FileResponse(
                    BytesIO(
                        SiteLogSerializer(
                            instance=site,
                            published=None
                        ).format(request.accepted_renderer.format).encode()
                    ),
                    filename=site.get_filename(
                        log_format=request.accepted_renderer.format,
                        epoch=datetime.now(),
                        name_len=request.GET.get('name_len', 9),
                        lower_case=request.GET.get('lower_case', False)
                    )
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
        ModelClass = kwargs.pop('model')
        can_delete = issubclass(ModelClass, SiteSubSection)
        parents = [
            *bases,
            mixins.RetrieveModelMixin,
            mixins.ListModelMixin,
            mixins.UpdateModelMixin,
            mixins.CreateModelMixin
        ]
        if can_delete:
            parents.append(mixins.DestroyModelMixin)

        parents.append(viewsets.GenericViewSet)
        obj = super().__new__(metacls, name, tuple(parents), namespace)

        class ViewSetFilter(FilterSet):
            site = django_filters.CharFilter(
                field_name='site__name',
                lookup_expr='iexact'
            )

            class Meta:
                model = ModelClass
                fields = [
                    'site',
                    'id'
                ] + (
                    ['subsection'] if issubclass(ModelClass, SiteSubSection)
                    else []
                )

        class ViewSetSerializer(ModelSerializer):

            serializer_field_mapping = {
                **ModelSerializer.serializer_field_mapping,
                models.DateTimeField: SLMDateTimeField
            }

            _diff = serializers.SerializerMethodField(read_only=True)
            _flags = serializers.JSONField(
                read_only=False,
                required=False,
                encoder=SiteSection._meta.get_field('_flags').encoder,
                decoder=SiteSection._meta.get_field('_flags').decoder
            )

            can_publish = serializers.SerializerMethodField(read_only=True)

            publish = serializers.BooleanField(write_only=True, required=False)

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
                    if (
                        value == '' and
                        getattr(
                            self.fields.get(field, None),
                            'allow_null',
                            False
                        )
                    ):
                        data[field] = None

                # if these are set to None - validation rejects them
                # todo anything else like this?
                if data.get('id', False) in {None, ''}:
                    del data['id']

                if data.get('subsection', False) in {None, ''}:
                    del data['subsection']

                return super().to_internal_value(data)

            def get_can_publish(self, obj):
                if 'request' in self.context:
                    return self.context['request'].user.is_moderator()
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
                        * Set instance (old or added) to published and issue
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
                    site = validated_data.get('site') or instance.site
                    is_moderator = site.is_moderator(
                        self.context['request'].user
                    )
                    do_publish = validated_data.pop('publish', False)
                    update_status = None

                    if not is_moderator:
                        # non-moderators are not allowed to publish!
                        if do_publish:
                            raise PermissionDenied(_(
                                'You must have moderator privileges to '
                                'publish site log edits.'
                            ))

                        # we don't disallow an accompanying edit with _flags -
                        # we just strip them out of the user doesnt have
                        # permission to add them
                        validated_data.pop('_flags', None)

                    section_id = validated_data.pop('id', None)
                    subsection = validated_data.get('subsection', None)

                    # get the previous section instance - if it exists
                    if instance is None:
                        # this is either a section where only one can exist or
                        # a subsection where multiple can exist
                        if not self.allow_multiple():
                            instance = ModelClass.objects.filter(
                                site=site
                            ).order_by('-edited').select_for_update().first()
                        # this is a subsection - if the subsection IDs are not
                        # present it is
                        elif subsection is not None:
                            instance = ModelClass.objects.filter(
                                site=site,
                                subsection=subsection
                            ).order_by('-edited').select_for_update().first()
                    else:
                        instance = ModelClass.objects.filter(
                            pk=instance.pk
                        ).select_for_update().first()

                    try:
                        # this is a new section
                        if instance is None:
                            new_section = super().create(validated_data)
                            new_section.full_clean()
                            new_section.save()
                            update_status = new_section.edited
                            slm_signals.section_added.send(
                                sender=self,
                                site=site,
                                user=self.context['request'].user,
                                request=self.context['request'],
                                timestamp=update_status,
                                section=new_section
                            )
                            instance = new_section
                        else:
                            # if an object id was present and it is not at or past
                            # the last section ID - we have a concurrent edit race
                            # condition between one or more users.
                            if section_id is not None and section_id < instance.id:
                                raise DRFValidationError(
                                    _(
                                        'Edits must be made on HEAD. Someone else '
                                        'may be editing the log concurrently. '
                                        'Refresh and try again.'
                                    )
                                )


                        # if not new - does this section have edits?
                        update = False
                        flags = validated_data.get('_flags', instance._flags)
                        edited_fields = []
                        for field in ModelClass.site_log_fields():
                            if field in validated_data:
                                is_many = isinstance(
                                    instance._meta.get_field(field),
                                    models.ManyToManyField
                                )
                                new_value = validated_data.get(field)
                                if (
                                    not is_many and
                                    new_value != getattr(instance, field)) or (
                                    is_many and set(new_value) != set(
                                        getattr(instance, field).all()
                                    )
                                ):
                                    update = True
                                    if not instance.published:
                                        edited_fields.append(field)
                                        if is_many:
                                            getattr(instance, field).set(
                                                new_value
                                            )
                                        else:
                                            setattr(instance, field, new_value)
                                    if field in flags:
                                        del flags[field]

                        if update:
                            if instance.published:
                                validated_data['_flags'] = flags
                                instance.pk = None  # copy the instance
                                instance.published = False
                                instance.save()
                                for param, value in validated_data.items():
                                    if isinstance(
                                        instance._meta.get_field(param),
                                        models.ManyToManyField
                                    ):
                                        getattr(instance, param).set(value)
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
                            slm_signals.section_edited.send(
                                sender=self,
                                site=site,
                                user=self.context['request'].user,
                                request=self.context['request'],
                                timestamp=update_status,
                                section=instance,
                                fields=edited_fields
                            )
                        elif '_flags' in validated_data:
                            # this is just a flag update
                            added = (
                                len(flags) -
                                (len(instance._flags) if instance._flags else 0)
                            )
                            site.num_flags += added
                            if site.num_flags < 0:
                                site.num_flags = 0

                            site.save()
                            instance._flags = flags
                            instance.save()

                        if do_publish:
                            update_status = update_status or now()
                            instance.publish(
                                request=self.context.get('request', None),
                                timestamp=update_status,
                                update_site=False
                            )
                            instance.refresh_from_db()

                        if update_status:
                            instance.site.update_status(
                                save=True,
                                user=self.context['request'].user,
                                timestamp=update_status
                            )
                        return instance
                    except DjangoValidationError as ve:
                        raise DRFValidationError(ve.message_dict)

            def update(self, instance, validated_data):
                return self.perform_section_update(
                    validated_data=validated_data,
                    instance=instance
                )

            def create(self, validated_data):
                return self.perform_section_update(
                    validated_data=validated_data
                )

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
                    relation_info.related_model,
                    'API_RELATED_FIELD',
                    None
                )
                _, defaults = super().build_relational_field(
                    field_name, relation_info
                )
                if related:
                    return (
                        SlugRelatedField,
                        {**defaults, 'slug_field': related}
                    )
                return _, defaults

            class Meta:
                model = ModelClass
                fields = [
                    'site',
                    'id',
                    'publish',
                    'published',
                    'can_publish',
                    '_flags',
                    '_diff',
                    *ModelClass.site_log_fields()
                ] + ([
                     'subsection',
                     'heading',
                     'effective',
                     'is_deleted'
                ] if issubclass(ModelClass, SiteSubSection) else [])

                extra_kwargs = {
                    'id': {
                        'required': False,
                        'read_only': False
                    },
                    'site': {
                        'required': True
                    },
                    **({
                        'heading': {'required': False, 'read_only': True},
                        'effective': {'required': False, 'read_only': True},
                        'is_deleted': {'required': False, 'read_only': True},
                        'subsection': {'required': False},
                        'four_character_id': {  # special case
                            'required': False, 'read_only': True
                        }
                    } if issubclass(ModelClass, SiteSubSection) else {})
                }

        obj.serializer_class = ViewSetSerializer
        obj.filterset_class = ViewSetFilter
        obj.permission_classes = (
            IsAuthenticated,
            CanEditSite,
            UpdateAdminOnly
        )
        obj.pagination_class = DataTablesPagination
        obj.filter_backends = (DjangoFilterBackend,)

        def get_queryset(self):
            return ModelClass.objects.editable_by(
                self.request.user
            ).select_related('site', 'editor')

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
                status=status.HTTP_201_CREATED,
                headers=headers
            )

        def destroy(self, request, *args, **kwargs):
            instance = self.get_object()
            instance = self.perform_destroy(instance)
            if instance:
                serializer = self.get_serializer(instance=instance)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data,
                    status=status.HTTP_200_OK,
                    headers=headers
                )
            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

        def perform_destroy(self, instance):
            with transaction.atomic():
                section = ModelClass.objects.select_for_update().get(
                    pk=instance.pk
                )
                if isinstance(section, SiteSubSection):
                    if ModelClass.objects.filter(
                        site=section.site,
                        subsection=section.subsection
                    ).order_by('-edited').first() != section:

                        raise serializers.ValidationError(
                            _(
                                'Edits must be made on HEAD. Someone else may '
                                'be editing the log concurrently. Refresh and '
                                'try again.'
                            )
                        )

                    previous = ModelClass.objects.filter(
                        site=section.site,
                        subsection=section.subsection,
                        published=True
                    )
                else:
                    previous = ModelClass.objects.filter(
                        site=section.site,
                        published=True
                    )

                if previous.count() == 0:
                    # we delete it if this section or subsection has never
                    # been published before
                    section.delete()
                    instance.site.update_status(
                        save=True,
                        user=self.request.user,
                        timestamp=now()
                    )
                    return None

                if not section.is_deleted:
                    # if it has been published before we copy and save it with
                    # the is_deleted flag set to True
                    section.pk = None  # this is how you copy a model
                    section.is_deleted = True
                    section.published = False
                    section.editor = self.request.user
                    section.save()
                    slm_signals.section_deleted.send(
                        sender=self,
                        site=section.site,
                        user=self.request.user,
                        request=self.request,
                        timestamp=now(),
                        section=section
                    )
                    instance.site.update_status(
                        save=True,
                        user=self.request.user,
                        timestamp=now()
                    )
                return section

        obj.get_queryset = get_queryset
        if can_delete:
            obj.perform_destroy = perform_destroy
            obj.destroy = destroy
        obj.create = create
        return obj


# TODO all these can be constructed dynamically from the models
class SiteFormViewSet(metaclass=SectionViewSet, model=SiteForm):
    pass


class SiteIdentificationViewSet(
    metaclass=SectionViewSet,
    model=SiteIdentification
):
    pass


class SiteLocationViewSet(metaclass=SectionViewSet, model=SiteLocation):
    pass


class SiteReceiverViewSet(metaclass=SectionViewSet, model=SiteReceiver):
    pass


class SiteAntennaViewSet(metaclass=SectionViewSet, model=SiteAntenna):
    pass


class SiteSurveyedLocalTiesViewSet(
    metaclass=SectionViewSet,
    model=SiteSurveyedLocalTies
):
    pass


class SiteFrequencyStandardViewSet(
    metaclass=SectionViewSet,
    model=SiteFrequencyStandard
):
    pass


class SiteCollocationViewSet(metaclass=SectionViewSet, model=SiteCollocation):
    pass


class SiteHumiditySensorViewSet(
    metaclass=SectionViewSet,
    model=SiteHumiditySensor
):
    pass


class SitePressureSensorViewSet(
    metaclass=SectionViewSet,
    model=SitePressureSensor
):
    pass


class SiteTemperatureSensorViewSet(
    metaclass=SectionViewSet,
    model=SiteTemperatureSensor
):
    pass


class SiteWaterVaporRadiometerViewSet(
    metaclass=SectionViewSet,
    model=SiteWaterVaporRadiometer
):
    pass


class SiteOtherInstrumentationViewSet(
    metaclass=SectionViewSet,
    model=SiteOtherInstrumentation
):
    pass


class SiteRadioInterferencesViewSet(
    metaclass=SectionViewSet,
    model=SiteRadioInterferences
):
    pass


class SiteMultiPathSourcesViewSet(
    metaclass=SectionViewSet,
    model=SiteMultiPathSources
):
    pass


class SiteSignalObstructionsViewSet(
    metaclass=SectionViewSet,
    model=SiteSignalObstructions
):
    pass


class SiteLocalEpisodicEffectsViewSet(
    metaclass=SectionViewSet,
    model=SiteLocalEpisodicEffects
):
    pass


class SiteOperationalContactViewSet(
    metaclass=SectionViewSet,
    model=SiteOperationalContact
):
    pass


class SiteResponsibleAgencyViewSet(
    metaclass=SectionViewSet,
    model=SiteResponsibleAgency
):
    pass


class SiteMoreInformationViewSet(
    metaclass=SectionViewSet,
    model=SiteMoreInformation
):
    pass


class SiteFileUploadViewSet(
    DataTablesListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):

    logger = getLogger('slm.api.edit.views.SiteFileUploadViewSet')

    serializer_class = SiteFileUploadSerializer
    permission_classes = (IsAuthenticated, CanEditSite,)
    parser_classes = (
        MultiPartParser,
        FormParser,
        JSONParser,
        FileUploadParser
    )

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
        13: SiteMoreInformationViewSet
    }

    @staticmethod
    def get_subsection_id(section):
        if section.section_number in {
            3, 4, 5, 6, 7, 8, 9, 10
        }:
            return section.ordering_id
        return None

    class FileFilter(AcceptListArguments, FilterSet):

        name = django_filters.CharFilter(
            field_name='name',
            lookup_expr='istartswith'
        )

        file_type = django_filters.MultipleChoiceFilter(
            choices=SLMFileType.choices
        )

        log_format = django_filters.MultipleChoiceFilter(
            choices=SiteLogFormat.choices
        )

        status = django_filters.MultipleChoiceFilter(
            choices=SiteFileUploadStatus.choices
        )

        class Meta:
            model = SiteFileUpload
            fields = (
                'name',
                'status',
                'file_type',
                'log_format'
            )

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = FileFilter
    ordering_fields = [
        '-timestamp',
        'name'
    ]

    original_request = None

    def dispatch(self, request, *args, **kwargs):
        self.site = kwargs.pop('site', None)
        self.original_request = request
        try:
            self.site = Site.objects.get(name__iexact=self.site)
        except Site.DoesNotExist:
            return HttpResponseNotFound(f'{self.site} does not exist.')

        if not self.site.can_edit(request.user):
            return HttpResponseForbidden(
                f'{request.user} cannot edit site {self.site.name}'
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return SiteFileUpload.objects.available_to(
            self.request.user
        ).filter(site=self.site)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():

            if 'file' not in request.FILES:
                return Response(
                    f"Expected a file upload with name 'file'.",
                    status=400
                )

            upload = SiteFileUpload(
                site=self.site,
                file=request.FILES['file'],
                name=request.FILES['file'].name[:255],
                user=request.user
            )
            upload.save()
            slm_signals.site_file_uploaded.send(
                sender=self,
                site=self.site,
                user=request.user,
                timestamp=upload.timestamp,
                request=request,
                upload=upload
            )

            if upload.file_type is SLMFileType.SITE_LOG:
                from slm.parsing.legacy import SiteLogBinder, SiteLogParser
                if upload.log_format is SiteLogFormat.LEGACY:
                    with upload.file.open() as uplf:
                        content = uplf.read()
                        bound_log = SiteLogBinder(
                            SiteLogParser(
                                content.decode(),
                                site_name=self.site.name
                            )
                        ).parsed
                        if not bound_log.errors:
                            self.update_from_legacy(request, bound_log)

                        upload.context = bound_log.context
                        if bound_log.errors:
                            upload.status = SiteFileUploadStatus.INVALID
                            upload.save()
                            return Response(
                                _('There were errors parsing the site log.'),
                                status=400
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
                        parsed = SiteLogParser(
                            content.decode(),
                            site_name=self.site.name
                        )

                        upload.context = parsed.context
                        if parsed.errors:
                            upload.status = SiteFileUploadStatus.INVALID
                            upload.save()
                            return Response(_(
                                'There were errors parsing the site log.'
                                ),
                                status=400
                            )
                        upload.save()
                        return Response(
                            f'GeodesyML uploads are not yet supported.',
                            status=400
                        )

                elif upload.log_format is SiteLogFormat.JSON:
                    return Response(
                        f'JSON uploads are not yet supported.',
                        status=400
                    )
                else:
                    return Response(
                        f'Unsupported site log upload format.',
                        status=400
                    )
        upload.site.refresh_from_db()
        return Response(
            self.get_serializer(instance=upload).data,
            status=200
        )

    def perform_update(self, serializer):
        # do permissions check on publish/unpublish action - also only allow
        # a subset of status changes
        if (
            serializer.validated_data.get('status', None) is not None and
            serializer.validated_data['status'] != serializer.instance.status
            and not self.site.can_publish(self.request.user)
        ):
            raise PermissionDenied(
                f'Must be a moderator to publish site files.'
            )
        if serializer.validated_data.get('status', None) and (
            SiteFileUploadStatus(serializer.validated_data['status']) not in {
                SiteFileUploadStatus.PUBLISHED,
                SiteFileUploadStatus.UNPUBLISHED
            }
        ):
            raise PermissionDenied(
                f'Files may only be published or unpublished.'
            )
        super().perform_update(serializer)

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
            10: set()
        }
        with transaction.atomic():
            for index, section in parsed.sections.items():
                if section.example or not section.contains_values:
                    continue

                section_view = self.SECTION_VIEWS.get(
                    section.heading_index,
                    None
                )
                if section_view:
                    data = {
                        **section.binding,
                        'site': self.site.id
                    }
                    subsection_number = self.get_subsection_id(section)
                    if subsection_number is not None:
                        # we have to find the right subsection identifiers
                        # (which don't necessarily equal the existing ids)
                        existing_sections.setdefault(
                            section.heading_index,
                            []
                        )
                        if not existing_sections[section.heading_index]:
                            existing_sections[section.heading_index] = list(
                                section_view.serializer_class.Meta.model.
                                    objects.filter(
                                        site=self.site,
                                        is_deleted=False
                                ).head().order_by('subsection')
                            )

                        if (
                            len(existing_sections[section.heading_index]) >
                            subsection_number - 1
                        ):
                            instance = existing_sections[
                                section.heading_index
                            ][subsection_number - 1]
                            data['subsection'] = instance.subsection
                            posted_subsections[section.heading_index].add(
                                instance
                            )

                    serializer = section_view.serializer_class(
                        data=data,
                        context={'request': request}
                    )
                    if not serializer.is_valid(raise_exception=False):
                        errors[index] = {
                            param: "\n".join(
                                [str(detail) for detail in details]
                            )
                            for param, details in serializer.errors.items()
                        }
                    else:
                        try:
                            serializer.save()
                        except DjangoValidationError as dve:
                            for param, error_list in dve.message_dict.items():
                                errors.setdefault(
                                    index, {}
                                )[param] = '\n'.join(
                                    [str(msg) for msg in error_list]
                                )

            if errors:
                # if any section fails - rollback all sections
                transaction.set_rollback(True)
                for section_index, section_errors in errors.items():
                    for param, error in section_errors.items():
                        section = parsed.sections[section_index]
                        param = section.get_param(param)
                        if param:
                            for line_no in range(
                                    param.line_no,
                                    param.line_end+1
                            ):
                                parsed.add_finding(
                                    Error(
                                        line_no,
                                        parsed,
                                        str(error),
                                        section=section
                                    )
                                )
                        else:
                            parsed.add_finding(
                                Error(
                                    section.line_no,
                                    parsed,
                                    str(error),
                                    section=section
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
                    except:
                        # catch everything here - if this does not happen
                        # its not the end of the world - the exception log
                        # will notify the relevant parties that there's some
                        # kind of issue
                        self.logger.exception(
                            'Error deleting subsection %d of section %s',
                            instance.subsection,
                            heading_index
                        )
        return errors
