from slm.api.permissions import (
    CanEditSite,
    IsUserOrAdmin,
    UpdateAdminOnly,
    CanDeleteAlert,
    IsAdmin
)
from rest_framework.permissions import IsAuthenticated

from rest_framework.filters import (
    SearchFilter,
    OrderingFilter
)
from django.db.models import (
    Q,
    OuterRef,
    Subquery,
    Count,
    F,
    IntegerField,
    Prefetch,
    Max,
    Window,
    RowRange
)
from django.http.response import Http404
from slm.utils import to_bool
from rest_framework import (
    viewsets,
    mixins,
    status,
    serializers
)
from rest_framework.serializers import ModelSerializer
from urllib.parse import unquote_plus
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import (
    DjangoFilterBackend,
    FilterSet
)
from django.db import transaction
import django_filters
from rest_framework.response import Response
from slm.defines import SiteLogStatus
from slm.api.edit.serializers import (
    StationListSerializer,
    UserSerializer,
    LogEntrySerializer,
    AlertSerializer
)
from slm.api.serializers import SiteLogSerializer
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from slm.models import (
    Site,
    SiteSubSection,
    UserProfile,
    SiteForm,
    SiteIdentification,
    SiteLocation,
    SiteReceiver,
    SiteAntenna,
    AntennaType,
    SiteSurveyedLocalTies,
    SiteFrequencyStandard,
    SiteCollocation,
    SiteHumiditySensor,
    SitePressureSensor,
    SiteTemperatureSensor,
    SiteWaterVaporRadiometer,
    SiteOtherInstrumentation,
    SiteRadioInterferences,
    SiteMultiPathSources,
    SiteSignalObstructions,
    SiteLocalEpisodicEffects,
    SiteOperationalContact,
    SiteResponsibleAgency,
    SiteMoreInformation,
    UserProfile,
    Agency,
    LogEntry,
    Alert
)
from slm.api.pagination import DataTablesPagination
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.http import HttpResponse
from rest_framework import viewsets, renderers
import json
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from ipware import get_client_ip


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
    permission_classes = (CanEditSite,)

    class StationFilter(FilterSet):

        name = django_filters.CharFilter(field_name='name', lookup_expr='istartswith')
        published_before = django_filters.CharFilter(field_name='last_publish', lookup_expr='lt')
        published_after = django_filters.CharFilter(field_name='last_publish', lookup_expr='gte')
        updated_before = django_filters.CharFilter(field_name='last_update', lookup_expr='lt')
        updated_after = django_filters.CharFilter(field_name='last_update', lookup_expr='gte')
        agency = django_filters.CharFilter(field_name='agencies__name', lookup_expr='iexact')

        class Meta:
            model = Site
            fields = (
                'name',
                'published_before',
                'published_after',
                'updated_before',
                'updated_after',
                'agency',
                'status'
            )

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = StationFilter
    ordering_fields = ['name', 'num_flags', 'created', 'last_update', 'last_publish']
    ordering = ('name',)

    def get_queryset(self):
        return Site.objects.accessible_by(self.request.user).prefetch_related('agencies').select_related('owner')


class LogEntryViewSet(DataTablesListMixin, viewsets.GenericViewSet):
    serializer_class = LogEntrySerializer
    permission_classes = (IsAuthenticated,)

    class LogEntryFilter(FilterSet):

        site = django_filters.CharFilter(field_name='site__name', lookup_expr='iexact')
        user = django_filters.CharFilter(field_name='user__email', lookup_expr='iexact')
        before = django_filters.CharFilter(field_name='timestamp', lookup_expr='lt')
        after = django_filters.CharFilter(field_name='timestamp', lookup_expr='gte')
        ip = django_filters.CharFilter(field_name='ip', lookup_expr='iexact')

        class Meta:
            model = LogEntry
            fields = ('site', 'user', 'before', 'after', 'ip')

    filter_backends = (DjangoFilterBackend,)
    filterset_class = LogEntryFilter

    def get_queryset(self):
        return LogEntry.objects.accessible_by(self.request.user).prefetch_related('site_log_object')


class AlertViewSet(DataTablesListMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = AlertSerializer
    permission_classes = (IsAuthenticated, CanDeleteAlert)

    class AlertFilter(FilterSet):

        site = django_filters.CharFilter(field_name='site__name', lookup_expr='iexact')
        user = django_filters.CharFilter(field_name='user__email', lookup_expr='iexact')
        agency = django_filters.CharFilter(field_name='agency__name', lookup_expr='iexact')

        class Meta:
            model = Alert
            fields = ('site', 'user', 'agency')

    filter_backends = (DjangoFilterBackend,)
    filterset_class = AlertFilter

    def get_queryset(self):
        return Alert.objects.accessible_by(self.request.user).select_related('user', 'site', 'agency')


class UserProfileViewSet(
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = UserSerializer
    permission_classes = (IsUserOrAdmin,)

    def get_queryset(self):
        return get_user_model().objects.filter(id=self.request.user.id).select_related('profile', 'agency')

    def list(self, request, **kwargs):
        resp = super(UserProfileViewSet, self).list(request, **kwargs)
        resp.data = resp.data[0]
        return resp

    def create(self, request, *args, **kwargs):
        kwargs[self.lookup_url_kwarg or self.lookup_field] = self.request.user.pk
        self.update(request, *args, **kwargs)


class SiteLogDownloadViewSet(
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Site.objects.all()

    lookup_field = 'name'
    lookup_url_kwarg = 'site'
    renderer_classes = (LegacyRenderer,)

    serializer_class = SiteLogSerializer

    def retrieve(self, request, *args, **kwargs):
        site = self.get_object()
        site_form = site.siteform_set.head()
        if site_form and site_form.date_prepared:
            timestamp = site_form.date_prepared
        else:
            timestamp = now()
        # todo should name timestamp be based on last edits?
        filename = f'{site.name}_{timestamp.year}{timestamp.month}{timestamp.day}.log'
        response = HttpResponse(
            getattr(
                self.get_serializer(
                    instance=site,
                    epoch=self.request.GET.get('epoch', None),
                    published=to_bool(self.request.GET.get('published', True)) or None
                ),
                kwargs.get('format', 'text')
            )  # todo can renderer just handle this?
        )
        if to_bool(kwargs.get('download', True)) and response.status_code < 400:
            response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)
        return response


class SectionViewSet(type):

    def __new__(metacls, name, bases, namespace, **kwargs):
        ModelClass = kwargs.pop('model')
        obj = super().__new__(
            metacls,
            name,
            (
                *bases,
                mixins.RetrieveModelMixin,
                mixins.ListModelMixin,
                mixins.UpdateModelMixin,
                mixins.CreateModelMixin,
                mixins.DestroyModelMixin,
                viewsets.GenericViewSet
            ),
            namespace
        )

        class ViewSetFilter(FilterSet):
            site = django_filters.CharFilter(field_name='site__name', lookup_expr='iexact')

            class Meta:
                model = ModelClass
                fields = ['site', 'id'] + ['subsection'] if issubclass(ModelClass, SiteSubSection) else []

        class ViewSetSerializer(ModelSerializer):

            _diff = serializers.SerializerMethodField(read_only=True)

            def get__diff(self, obj):
                return obj.published_diff()

            def update(self, instance, validated_data):
                if '_flags' in validated_data:
                    # let the log generator know that this is just a flag update
                    instance._flag_update = True
                elif 'published' in validated_data:
                    instance._publisher = self.context['request'].user
                instance._ip = get_client_ip(self.context['request'])[0]
                return super().update(instance, validated_data)

            def create(self, validated_data):
                with transaction.atomic():
                    site = validated_data.get('site')
                    # if id is present we use it to make sure this edit is taking place on HEAD, otherwise we just
                    # allow it
                    validated_data.pop('published')  # dont allow edits to published here - must go through admin
                    section_id = validated_data.pop('id', None)
                    subsection = validated_data.get('subsection', None)
                    validated_data['editor'] = self.context['request'].user

                    qry = Q(site=site)
                    if subsection is not None:
                        qry &= Q(subsection=subsection)

                    if section_id is None and subsection is None and issubclass(ModelClass, SiteSubSection):
                        # this is a new subsection
                        new_section = super().create(validated_data)
                        new_section.full_clean()
                        new_section.save()
                        return new_section

                    existing = ModelClass.objects.filter(qry).order_by('-edited').select_for_update().first()
                    if not existing:
                        # todo how to pass IP to logger signal handler?
                        new_section = super().create(validated_data)
                        new_section.full_clean()
                        new_section.save()
                        return new_section

                    existing.edited = now()
                    existing._ip = get_client_ip(self.context['request'])[0]
                    if section_id and existing.id != section_id:
                        raise serializers.ValidationError('Edits must be made on HEAD. Refresh and try again.')

                    update = False
                    flags = existing._flags
                    for field in ModelClass.site_log_fields():
                        new_value = validated_data.get(field, None)
                        if new_value != getattr(existing, field):
                            update = True
                            if not existing.published:
                                setattr(existing, field, new_value)
                            if field in flags:
                                del flags[field]

                    if update:
                        if existing.published:
                            validated_data['_flags'] = flags
                            new_section = super().create(
                                validated_data,
                            )
                            new_section.full_clean()
                            new_section.save()
                            return new_section
                        else:
                            existing._flags = flags
                            existing.full_clean()
                            existing.save()
                    return existing

            class Meta:
                model = ModelClass
                fields = ['site', 'id', 'published', '_flags', '_diff', *ModelClass.site_log_fields()] + \
                    ([
                         'subsection',
                         'heading',
                         'effective',
                         'is_deleted'
                     ] if issubclass(ModelClass, SiteSubSection) else [])
                extra_kwargs = {
                    '_flags': {
                        'read_only': False,
                        'required': False
                    },
                    'id': {
                        'required': False,
                        'read_only': False
                    },
                    **({
                        'heading': {'required': False, 'read_only': True},
                        'effective': {'required': False, 'read_only': True},
                        'is_deleted': {'required': False, 'read_only': True},
                        'subsection': {'required': False}
                    } if issubclass(ModelClass, SiteSubSection) else {})
                }

        obj.serializer_class = ViewSetSerializer
        obj.filterset_class = ViewSetFilter
        obj.permission_classes = (CanEditSite, UpdateAdminOnly)
        obj.filter_backends = (DjangoFilterBackend,)

        def get_queryset(self):
            return ModelClass.objects.accessible_by(self.request.user).select_related('site', 'editor')

        def create(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                self.perform_create(serializer)
            except DjangoValidationError as ve:
                raise DRFValidationError(ve.message_dict)

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        def destroy(self, request, *args, **kwargs):
            instance = self.get_object()
            instance = self.perform_destroy(instance)
            serializer = self.get_serializer(instance=instance)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

        def perform_destroy(self, instance):
            with transaction.atomic():
                section = ModelClass.objects.select_for_update().get(pk=instance.pk)
                if isinstance(section, SiteSubSection):
                    if ModelClass.objects.filter(
                            site=section.site,
                            subsection=section.subsection
                    ).order_by('-edited').first() != section:
                        raise serializers.ValidationError('Edits must be made on HEAD. Refresh and try again.')

                if not section.is_deleted:
                    # this is how you copy a model in Django
                    section.pk = None
                    section.is_deleted = True
                    section.published = False
                    section.editor = self.request.user
                    section.save()
                return section

        obj.get_queryset = get_queryset
        obj.perform_destroy = perform_destroy
        obj.destroy = destroy
        obj.create = create
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


class SiteSurveyedLocalTiesViewSet(metaclass=SectionViewSet, model=SiteSurveyedLocalTies):
    pass


class SiteFrequencyStandardViewSet(metaclass=SectionViewSet, model=SiteFrequencyStandard):
    pass


class SiteCollocationViewSet(metaclass=SectionViewSet, model=SiteCollocation):
    pass


class SiteHumiditySensorViewSet(metaclass=SectionViewSet, model=SiteHumiditySensor):
    pass


class SitePressureSensorViewSet(metaclass=SectionViewSet, model=SitePressureSensor):
    pass


class SiteTemperatureSensorViewSet(metaclass=SectionViewSet, model=SiteTemperatureSensor):
    pass


class SiteWaterVaporRadiometerViewSet(metaclass=SectionViewSet, model=SiteWaterVaporRadiometer):
    pass


class SiteOtherInstrumentationViewSet(metaclass=SectionViewSet, model=SiteOtherInstrumentation):
    pass


class SiteRadioInterferencesViewSet(metaclass=SectionViewSet, model=SiteRadioInterferences):
    pass


class SiteMultiPathSourcesViewSet(metaclass=SectionViewSet, model=SiteMultiPathSources):
    pass


class SiteSignalObstructionsViewSet(metaclass=SectionViewSet, model=SiteSignalObstructions):
    pass


class SiteLocalEpisodicEffectsViewSet(metaclass=SectionViewSet, model=SiteLocalEpisodicEffects):
    pass


class SiteOperationalContactViewSet(metaclass=SectionViewSet, model=SiteOperationalContact):
    pass


class SiteResponsibleAgencyViewSet(metaclass=SectionViewSet, model=SiteResponsibleAgency):
    pass


class SiteMoreInformationViewSet(metaclass=SectionViewSet, model=SiteMoreInformation):
    pass
