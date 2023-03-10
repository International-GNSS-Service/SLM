"""
Handles forms for site log sections, user
management.

There is a form for each sitelog section.

More info on forms:
https://docs.djangoproject.com/en/3.2/topics/forms/

More info on field types:
https://docs.djangoproject.com/en/3.2/ref/models/fields/
"""
from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.core.validators import MinValueValidator
from django.db import transaction
from django.db.models import Max
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.urls import reverse_lazy
from django.db.models.fields import NOT_PROVIDED
from django_enum.forms import EnumChoiceField
from django.forms.fields import (
    TypedMultipleChoiceField,
    BooleanField
)
from django.forms.widgets import (
    CheckboxInput,
    CheckboxSelectMultiple,
    HiddenInput
)
from django.utils.functional import Promise
from slm.api.edit.serializers import UserProfileSerializer, UserSerializer
from slm.defines import (
    SLMFileType,
    SiteLogStatus,
    AlertLevel,
    ISOCountry,
    FrequencyStandardType
)
from slm.widgets import (
    AutoComplete,
    SLMCheckboxSelectMultiple,
    SLMDateTimeWidget,
    DatePicker,
    AutoCompleteSelectMultiple,
    AutoCompleteEnumSelectMultiple,
    EnumSelectMultiple
)
from slm.models import (
    Alert,
    Agency,
    Network,
    SatelliteSystem,
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
    SiteSignalObstructions,
    SiteSurveyedLocalTies,
    SiteTemperatureSensor,
    SiteWaterVaporRadiometer,
    Receiver,
    Antenna,
    Radome
)
from django.utils.functional import SimpleLazyObject
from slm.utils import to_snake_case
from ckeditor.widgets import CKEditorWidget
from crispy_forms.layout import Layout, Div, Field
from crispy_forms.helper import FormHelper
import json


class SLMCheckboxInput(CheckboxInput):
    """
    Django's BooleanField/NullBooleanField does not properly handle value ==
    'on' or value == 'off' which are submitted as form data for checkboxes and
    switches in certain circumstances. We Provide our own extensions here that
    do this. This might change in the future and if so these fields can be
    deleted and replaced by the Django internal ones.
    """

    def format_value(self, value):
        if isinstance(value, list):
            value = value[0]
        return {
            'on': 'true',
            'off': 'false'
        }.get(
            value.lower() if isinstance(value, str) else value,
            super().format_value(value)
        )

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if isinstance(value, list):
            value = value[0]
        return {
            'on': True,
            'off': False
        }.get(
            value.lower() if isinstance(value, str) else value,
            super().value_from_datadict(data, files, name)
        )


class SLMBooleanField(BooleanField):

    widget = SLMCheckboxInput

    def to_python(self, value):
        if isinstance(value, str) and value.lower() in ('false', '0', 'off'):
            value = False
        else:
            value = bool(value)
        return super().to_python(value)


class EnumMultipleChoiceField(EnumChoiceField, TypedMultipleChoiceField):
    """
    The default ``ChoiceField`` will only accept the base enumeration values.
    Use this field on forms to accept any value mappable to an enumeration
    including any labels or symmetric properties.
    """
    widget = EnumSelectMultiple

    def __init__(self, *args, **kwargs):
        coerce = self.coerce
        super().__init__(*args, **kwargs)
        self.coerce = coerce

    def coerce(self, value):
        if isinstance(value, self.enum):
            return value
        return [
            super(EnumMultipleChoiceField, self).coerce(val) for val in value
        ]


class SLMDateField(forms.DateField):
    input_type = 'date'


class SLMTimeField(forms.TimeField):
    input_type = 'time'


class SLMDateTimeField(forms.SplitDateTimeField):

    widget = SLMDateTimeWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.widgets[0].input_type = 'date'
        self.widget.widgets[1].input_type = 'time'


class AutoSelectMixin:

    def __init__(
            self,
            *args,
            value_param='id',
            label_param=None,
            render_suggestion=None,
            query_params=None,
            menu_class=None,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({
            'data-value-param': value_param
        })
        self.widget.attrs['data-value-param'] = value_param
        if label_param:
            self.widget.attrs['data-label-param'] = label_param
        if render_suggestion:
            self.widget.attrs['data-render-suggestion'] = render_suggestion
        if menu_class:
            self.widget.attrs['data-menu-class'] = menu_class
        if query_params:
            self.widget.attrs['data-query-params'] = (
                query_params
                if isinstance(query_params, str)
                else json.dumps(query_params)
            )
        self.widget.attrs['class'] = ' '.join([
            *self.widget.attrs.get('class', '').split(' '),
            'search-input'
        ])


class ModelAutoSelectMixin(AutoSelectMixin):

    def __init__(self, service_url, *args, search_param='search', **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs['data-service-url'] = service_url
        self.widget.attrs['data-search-param'] = search_param


class ModelAutoComplete(ModelAutoSelectMixin, forms.ModelChoiceField):
    widget = AutoComplete


class ModelMultipleAutoComplete(
    ModelAutoSelectMixin,
    forms.ModelMultipleChoiceField
):
    widget = AutoCompleteSelectMultiple


class EnumAutoSelectMixin(AutoSelectMixin):

    class PropertyEncoder(json.JSONEncoder):

        def default(self, obj):
            if isinstance(obj, Promise):
                return str(obj)
            return super().default(obj)

    def __init__(
            self,
            enum,
            *args,
            properties=None,
            data_source=None,
            **kwargs
    ):
        super().__init__(
            enum,
            *args,
            value_param=kwargs.pop('value_param', 'value'),
            label_param=kwargs.pop('label_param', 'label'),
            **kwargs
        )
        properties = set(properties or [])
        properties.update({'value', 'label'})

        def lazy_source():
            """
            Data sources might hit the database - so we have to evaluate them
            lazily at widget render time instead of before django bootstrapping
            """
            return json.dumps(sorted(
                [
                    {prop: getattr(en, prop) for prop in properties}
                    for en in (data_source() if data_source else enum or [])
                ],
                key=lambda en: en[self.widget.attrs['data-label-param']]),
                cls=MultiSelectEnumAutoComplete.PropertyEncoder
            )

        self.widget.attrs['data-source'] = SimpleLazyObject(lazy_source)


class MultiSelectEnumAutoComplete(
    EnumAutoSelectMixin,
    EnumMultipleChoiceField
):
    widget = AutoCompleteEnumSelectMultiple


class SelectEnumAutoComplete(EnumAutoSelectMixin, EnumChoiceField):
    widget = AutoComplete

    def __init__(self, *args, widget=AutoComplete, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


class NewSiteForm(forms.ModelForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_id = 'slm-new-site-form'
        helper.layout = Layout(
            Div(
                Div(
                    'name',
                    css_class='col-3'
                ),
                Div(
                    'agencies',
                    css_class='col-9'
                ),
                css_class='row'
            )
        )
        return helper

    agencies = ModelMultipleAutoComplete(
        queryset=Agency.objects.all(),
        help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Agency'),
        required=False,
        service_url=reverse_lazy('slm_edit_api:agency-list'),
        search_param='search',
        value_param='id',
        label_param='name',
        render_suggestion='return `(${obj.shortname}) ${obj.name}`;'
    )

    class Meta:
        model = Site
        fields = ['name', 'agencies']


class SectionForm(forms.ModelForm):

    def __init__(self, instance=None, **kwargs):
        self.diff = instance.published_diff() if instance else {}
        self.flags = instance._flags if instance else {}
        super().__init__(instance=instance, **kwargs)
        for field in self.fields:
            try:
                model_field = self.Meta.model._meta.get_field(field)
                self.fields[field].required = not (
                    getattr(model_field, 'default', None) != NOT_PROVIDED
                    and model_field.blank
                )
                self.fields[field].widget.attrs.setdefault('class', '')
                self.fields[field].widget.attrs['class'] += ' slm-form-field'
            except FieldDoesNotExist:
                pass

    @classmethod
    def section_name(cls):
        return to_snake_case(
            cls.Meta.model.__name__
        ).replace('_', ' ').replace('site', '').title().strip()

    @property
    def num_flags(self):
        return len(self.flags)

    @classmethod
    def api(cls):
        return f'slm_edit_api:{cls.Meta.model.__name__.lower()}'

    @cached_property
    def structured_fields(self):
        # todo this is spaghetti
        # arrange fields in structure to easily produce fieldsets in
        # correct order in the template, reflects old site
        # log order and groupings
        fields = []

        def flatten(structure):
            flat = []
            for field in structure:
                if isinstance(field, tuple) or isinstance(field, list):
                    flat += flatten(field)
                else:
                    flat.append(field)
            return flat

        def resolve_field(field_name):
            fields = []
            if field_name not in self.fields:
                if hasattr(getattr(self.Meta.model, field_name), 'field'):
                    field = getattr(self.Meta.model, field_name).field
                    if isinstance(field, tuple) or isinstance(field, list):
                        fields.extend([fd.name for fd in field])
                    else:
                        fields.append(field.name)
            else:
                fields.append(field_name)

            return [
                self.fields[field].get_bound_field(form=self, field_name=field)
                for field in fields
            ]

        for structure in self.Meta.model.structure():
            if isinstance(structure, tuple) or isinstance(structure, list):
                group_fields = []
                try:
                    self._meta.model._meta.get_field(structure[0])
                    group = None
                    group_fields.append(resolve_field(structure[0])[0])
                except FieldDoesNotExist:
                    group = structure[0]

                for field in flatten(structure[1]):
                    group_fields.extend(resolve_field(field))

                fields.append((group, group_fields))
            else:
                fields.append((None, resolve_field(structure)))
        fields += [(None, [field]) for field in self.hidden_fields()]
        return fields

    # todo this might be a security hole - restrict queryset to user's stations
    site = forms.ModelChoiceField(
        queryset=Site.objects.all(),
        widget=forms.HiddenInput()
    )

    id = forms.IntegerField(
        validators=[MinValueValidator(0)],
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        fields = ['site', 'id']


class SubSectionForm(SectionForm):

    subsection = forms.IntegerField(
        validators=[MinValueValidator(0)],
        widget=forms.HiddenInput(),
        required=False
    )

    def save(self, commit=True):
        if self.instance.subsection is None:
            with transaction.atomic():
                # todo is there a race condition here?
                self.instance.subsection = (
                    self.Meta.model.objects.select_for_update().filter(
                        site=self.instance.site
                    ).aggregate(Max('subsection'))['subsection__max'] or 0
                ) + 1

                return super().save(commit=commit)
        return super().save(commit=commit)

    @classmethod
    def group_name(cls):
        if hasattr(cls, 'NAV_HEADING'):
            return cls.NAV_HEADING.replace(
                ' ', '_'
            ).replace('.', '').strip().lower()
        return None

    class Meta(SectionForm.Meta):
        fields = [
            *SectionForm.Meta.fields,
            'subsection'
        ]


class SiteFormForm(SectionForm):

    class Meta(SectionForm.Meta):
        model = SiteForm
        fields = [
            *SectionForm.Meta.fields,
            *SiteForm.site_log_fields()
        ]
        widgets = {
            'date_prepared': DatePicker
        }


class SiteIdentificationForm(SectionForm):

    # we only include this for legacy purposes - this is not an editable value
    four_character_id = forms.CharField(
        label=_('Four Character ID'),
        help_text=_(
            'This is the 9 Character station name (XXXXMRCCC) used in RINEX 3 '
            'filenames. Format: (XXXX - existing four character IGS station '
            'name, M - Monument or marker number (0-9), R - Receiver number '
            '(0-9), CCC - Three digit ISO 3166-1 country code)'
        ),
        disabled=True,
        required=False
    )

    class Meta(SectionForm.Meta):
        model = SiteIdentification
        fields = [
            *SectionForm.Meta.fields,
            *SiteIdentification.site_log_fields(),
            'four_character_id'
        ]
        field_classes = {
            'date_installed': SLMDateTimeField
        }


class SiteLocationForm(SectionForm):

    country = SelectEnumAutoComplete(
        ISOCountry,
        help_text=SiteLocation._meta.get_field('country').help_text,
        label=SiteLocation._meta.get_field('country').verbose_name,
        render_suggestion=(
            'return `<span class="fi fi-${obj.value.toLowerCase()}"></span>'
            '<span class="matchable">${obj.label}</span>`;'
        ),
        strict=False
    )

    class Meta:
        model = SiteLocation
        fields = [
            *SectionForm.Meta.fields,
            *SiteLocation.site_log_fields()
        ]


class SiteReceiverForm(SubSectionForm):

    COPY_LAST_ON_ADD = [
        field for field in
        [
            *SubSectionForm.Meta.fields,
            *SiteReceiver.site_log_fields()
        ]
        if field not in {'installed', 'removed', 'additional_info'}
    ]

    satellite_system = forms.ModelChoiceField(
        queryset=SatelliteSystem.objects.all(),
        help_text=SiteReceiver._meta.get_field('satellite_system').help_text,
        label=SiteReceiver._meta.get_field('satellite_system').verbose_name,
        required=True,
        widget=SLMCheckboxSelectMultiple(columns=4),
        empty_label=None
    )

    receiver_type = ModelAutoComplete(
        queryset=Receiver.objects.all(),
        service_url=reverse_lazy('slm_public_api:receiver-list'),
        help_text=SiteReceiver._meta.get_field('receiver_type').help_text,
        label=SiteReceiver._meta.get_field('receiver_type').verbose_name,
        search_param='model',
        value_param='model',
        label_param='model'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # todo why is this not automatically done?
        if 'satellite_system' in self.initial:
            self.initial['satellite_system'] = [
                system.name for system in self.initial[
                    'satellite_system'
                ].all()
            ]

    class Meta(SubSectionForm):
        model = SiteReceiver
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteReceiver.site_log_fields()
        ]
        field_classes = {
            'installed': SLMDateTimeField,
            'removed': SLMDateTimeField
        }


class SiteAntennaForm(SubSectionForm):

    COPY_LAST_ON_ADD = [
        field for field in
        [
            *SubSectionForm.Meta.fields,
            *SiteAntenna.site_log_fields()
        ]
        if field not in {'installed', 'removed', 'additional_info'}
    ]

    alignment = forms.FloatField(
        required=SiteAntenna._meta.get_field('alignment').blank,
        help_text=SiteAntenna._meta.get_field('alignment').help_text,
        label=SiteAntenna._meta.get_field('alignment').verbose_name,
        max_value=180,
        min_value=-180
    )

    antenna_type = ModelAutoComplete(
        queryset=Antenna.objects.all(),
        service_url=reverse_lazy('slm_public_api:antenna-list'),
        help_text=SiteAntenna._meta.get_field('antenna_type').help_text,
        label=SiteAntenna._meta.get_field('antenna_type').verbose_name,
        search_param='model',
        value_param='model',
        label_param='model'
    )

    radome_type = ModelAutoComplete(
        queryset=Radome.objects.all(),
        service_url=reverse_lazy('slm_public_api:radome-list'),
        help_text=SiteAntenna._meta.get_field('radome_type').help_text,
        label=SiteAntenna._meta.get_field('radome_type').verbose_name,
        search_param='model',
        value_param='model',
        label_param='model'
    )

    class Meta(SubSectionForm):
        model = SiteAntenna
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteAntenna.site_log_fields()
        ]
        field_classes = {
            'installed': SLMDateTimeField,
            'removed': SLMDateTimeField
        }


class SiteSurveyedLocalTiesForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteSurveyedLocalTies
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteSurveyedLocalTies.site_log_fields()
        ]
        field_classes = {
            'measured': SLMDateTimeField
        }


class SiteFrequencyStandardForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteFrequencyStandard
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteFrequencyStandard.site_log_fields()
        ]
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class SiteCollocationForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteCollocation
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteCollocation.site_log_fields()
        ]
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class MeteorologicalForm(SubSectionForm):

    NAV_HEADING = _('Meteorological Instr.')

    class Meta(SubSectionForm):
        fields = SubSectionForm.Meta.fields
        widgets = {
            'calibration': DatePicker,
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class SiteHumiditySensorForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteHumiditySensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteHumiditySensor.site_log_fields()
        ]


class SitePressureSensorForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SitePressureSensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SitePressureSensor.site_log_fields()
        ]


class SiteTemperatureSensorForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteTemperatureSensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteTemperatureSensor.site_log_fields()
        ]


class SiteWaterVaporRadiometerForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteWaterVaporRadiometer
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteWaterVaporRadiometer.site_log_fields()
        ]


class SiteOtherInstrumentationForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteOtherInstrumentation
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteOtherInstrumentation.site_log_fields()
        ]


class LocalConditionForm(SubSectionForm):

    NAV_HEADING = _('Local Conditions')

    class Meta(SubSectionForm.Meta):
        fields = SubSectionForm.Meta.fields
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class SiteRadioInterferencesForm(LocalConditionForm):

    class Meta(LocalConditionForm.Meta):
        model = SiteRadioInterferences
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteRadioInterferences.site_log_fields()
        ]


class SiteMultiPathSourcesForm(LocalConditionForm):

    class Meta(LocalConditionForm.Meta):
        model = SiteMultiPathSources
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteMultiPathSources.site_log_fields()
        ]


class SiteSignalObstructionsForm(LocalConditionForm):

    class Meta(LocalConditionForm.Meta):
        model = SiteSignalObstructions
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteSignalObstructions.site_log_fields()
        ]


class SiteLocalEpisodicEffectsForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteLocalEpisodicEffects
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteLocalEpisodicEffects.site_log_fields()
        ]
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class AgencyPOCForm(SectionForm):

    class Meta(SectionForm.Meta):
        fields = SectionForm.Meta.fields
        widgets = {
            'agency': forms.Textarea(attrs={'rows': 1}),
            'mailing_address': forms.Textarea(attrs={'rows': 4})
        }


class SiteOperationalContactForm(AgencyPOCForm):

    class Meta(AgencyPOCForm.Meta):
        model = SiteOperationalContact
        fields = [
            *AgencyPOCForm.Meta.fields,
            *SiteOperationalContact.site_log_fields()
        ]


class SiteResponsibleAgencyForm(AgencyPOCForm):

    class Meta(AgencyPOCForm.Meta):
        model = SiteResponsibleAgency
        fields = [
            *AgencyPOCForm.Meta.fields,
            *SiteResponsibleAgency.site_log_fields()
        ]


class SiteMoreInformationForm(SectionForm):

    class Meta(SectionForm.Meta):
        model = SiteMoreInformation
        fields = [
            *SectionForm.Meta.fields,
            *SiteMoreInformation.site_log_fields()
        ]


class UserForm(forms.ModelForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_id = 'slm-user-form'
        helper.layout = Layout(
            Div(Div('email'), css_class='row'),
            Div(Div('first_name', css_class='col-6'), Div('last_name', css_class='col-6'), css_class='row'),
            Div(Div('silence_alerts', css_class='col-6'), Div('html_emails', css_class='col-6'), css_class='row'),
            Div(Div('agencies'), css_class='row')
        )
        return helper

    agencies = forms.ModelMultipleChoiceField(
        queryset=Agency.objects.all(),
        required=False,
        disabled=True
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        if instance:
            self.fields['agencies'].queryset = instance.agencies.all()

    class Meta:
        model = UserSerializer.Meta.model
        fields = UserSerializer.Meta.fields
        exclude = ('date_joined', 'profile')


class UserProfileForm(forms.ModelForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_id = 'slm-user-profile-form'
        helper.layout = Layout(
            Div(Div('phone1', css_class='col-6'), Div('phone2', css_class='col-6'), css_class='row'),
            Div(Div('address1'), css_class='row'),
            Div(Div('address2'), css_class='row'),
            Div(Div('address3'), css_class='row'),
            Div(Div('city', css_class='col-6'), Div('state_province', css_class='col-6'), css_class='row'),
            Div(Div('country', css_class='col-6'), Div('postal_code', css_class='col-6'), css_class='row')
        )
        return helper

    class Meta:
        model = UserProfileSerializer.Meta.model
        fields = UserProfileSerializer.Meta.fields
        exclude = ('registration_agency',)


class SiteFileForm(forms.ModelForm):

    name = forms.SlugField(
        max_length=255,
        help_text=_('The name of the file.')
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        if instance and instance.file_type != SLMFileType.SITE_IMAGE:
            self.fields['direction'].widget = forms.HiddenInput()
            self.fields['direction'].disabled = True

    class Meta:
        model = SiteFileUpload
        fields = [
            'name',
            'description',
            'direction'
        ]


class RichTextForm(forms.Form):

    text = forms.CharField(widget=CKEditorWidget(config_name='richtextinput'))


class StationFilterForm(forms.Form):
    """
    Todo - how to render help_text as alt or titles?
    """

    @property
    def helper(self):
        from crispy_forms.layout import Fieldset
        helper = FormHelper()
        helper.form_id = 'slm-station-filter'
        helper.disable_csrf = True
        helper.layout = Layout(
            Div(
                Div(
                    Field('status', css_class='slm-status'),
                    'alert',
                    Field('alert_level', css_class='slm-alert-level'),
                    css_class='col-3'
                ),
                Div(
                    Fieldset(
                        _('Equipment Filters'),
                        Field(
                            'current',
                            css_class="form-check-input",
                            wrapper_class="form-check form-switch"
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
                css_class='row'
            )
        )
        helper.attrs = {'data_slm_initial': json.dumps({
            field.name: field.field.initial
            for field in self if field.field.initial
        })}
        return helper

    name = forms.CharField(required=False)

    status = EnumMultipleChoiceField(
        SiteLogStatus,
        # help_text=_('Include stations with these statuses.'),
        label=_('Site Status'),
        required=False
    )

    alert = forms.MultipleChoiceField(
        choices=(
            (alert.__name__, alert._meta.verbose_name)
            for alert in Alert.objects.site_alerts()
        ),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        # help_text=_('Include stations with the following alert types.'),
    )

    alert_level = EnumMultipleChoiceField(
        AlertLevel,
        # help_text=_('Include stations with alerts at this level.'),
        label=_('Alert Level'),
        required=False
    )

    current = SLMBooleanField(
        label=_('Current'),
        help_text=_('Only include sites that currently have this equipment.'),
        initial=True,
        required=False
    )

    receiver = ModelMultipleAutoComplete(
        queryset=Receiver.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Receiver'),
        required=False,
        service_url=reverse_lazy('slm_public_api:receiver-list'),
        search_param='model',
        value_param='id',
        label_param='model',
        query_params={'in_use': True}
    )

    antenna = ModelMultipleAutoComplete(
        queryset=Antenna.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Antenna'),
        required=False,
        service_url=reverse_lazy('slm_public_api:antenna-list'),
        search_param='model',
        value_param='id',
        label_param='model',
        query_params={'in_use': True}
    )

    radome = ModelMultipleAutoComplete(
        queryset=Radome.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Radome'),
        required=False,
        service_url=reverse_lazy('slm_public_api:radome-list'),
        search_param='model',
        value_param='id',
        label_param='model',
        query_params={'in_use': True}
    )

    agency = ModelMultipleAutoComplete(
        queryset=Agency.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Agency'),
        required=False,
        service_url=reverse_lazy('slm_edit_api:agency-list'),
        search_param='search',
        value_param='id',
        label_param='name',
        render_suggestion=(
            'return `<span class="matchable">(${obj.shortname})</span>'
            '<span class="matchable">${obj.name}</span>`;'
        )
    )

    network = ModelMultipleAutoComplete(
        queryset=Network.objects.all(),
        # help_text=_('Enter the name of an IGS Network.'),
        label=_('Network'),
        required=False,
        service_url=reverse_lazy('slm_edit_api:network-list'),
        search_param='name',
        value_param='id',
        label_param='name'
    )

    country = MultiSelectEnumAutoComplete(
        # help_text=_('Enter the name of a country or region.'),
        ISOCountry,
        label=_('Country/Region'),
        required=False,
        render_suggestion=(
            'return `<span class="fi fi-${obj.value.toLowerCase()}"></span>'
            '<span class="matchable">${obj.label}</span>`;'
        ),
        data_source=ISOCountry.with_stations
    )


class PublicAPIStationFilterForm(forms.Form):
    """
    Todo - how to render help_text as alt or titles?
    """

    @property
    def helper(self):
        from crispy_forms.layout import Fieldset, Submit
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

    station = ModelMultipleAutoComplete(
        queryset=Site.objects.public(),
        service_url=reverse_lazy('slm_public_api:name-list'),
        #help_text=Site._meta.get_field('name').help_text,
        #label=Site._meta.get_field('name').verbose_name,
        search_param='name',
        value_param='name',
        label_param='name',
        menu_class='station-names',
        to_field_name='name',
        required=False
    )

    satellite_system = forms.ModelMultipleChoiceField(
        queryset=SatelliteSystem.objects.all(),
        label=SiteReceiver._meta.get_field('satellite_system').verbose_name,
        required=False,
        widget=CheckboxSelectMultiple()
    )

    frequency_standard = EnumMultipleChoiceField(
        FrequencyStandardType,
        required=False,
        label=_('Frequency Standard')
    )

    current = SLMBooleanField(
        label=_('Current'),
        help_text=_('Only include sites that currently have this equipment.'),
        initial=True,
        required=False
    )

    receiver = ModelMultipleAutoComplete(
        queryset=Receiver.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Receiver'),
        required=False,
        service_url=reverse_lazy('slm_public_api:receiver-list'),
        search_param='model',
        value_param='id',
        label_param='model',
        query_params={'in_use': True}
    )

    antenna = ModelMultipleAutoComplete(
        queryset=Antenna.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Antenna'),
        required=False,
        service_url=reverse_lazy('slm_public_api:antenna-list'),
        search_param='model',
        value_param='id',
        label_param='model',
        query_params={'in_use': True}
    )

    radome = ModelMultipleAutoComplete(
        queryset=Radome.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Radome'),
        required=False,
        service_url=reverse_lazy('slm_public_api:radome-list'),
        search_param='model',
        value_param='id',
        label_param='model',
        query_params={'in_use': True}
    )

    agency = ModelMultipleAutoComplete(
        queryset=Agency.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_('Agency'),
        required=False,
        service_url=reverse_lazy('slm_edit_api:agency-list'),
        search_param='search',
        value_param='id',
        label_param='name',
        render_suggestion=(
            'return `<span class="matchable">(${obj.shortname})</span>'
            '<span class="matchable">${obj.name}</span>`;'
        )
    )

    network = ModelMultipleAutoComplete(
        queryset=Network.objects.all(),
        # help_text=_('Enter the name of an IGS Network.'),
        label=_('Network'),
        required=False,
        service_url=reverse_lazy('slm_edit_api:network-list'),
        search_param='name',
        value_param='id',
        label_param='name'
    )

    country = MultiSelectEnumAutoComplete(
        # help_text=_('Enter the name of a country or region.'),
        ISOCountry,
        label=_('Country/Region'),
        required=False,
        render_suggestion=(
            'return `<span class="fi fi-${obj.value.toLowerCase()}"></span>'
            '<span class="matchable">${obj.label}</span>`;'
        ),
        data_source=ISOCountry.with_stations
    )

    def clean_current(self):
        # todo mixin that does this
        if not self['current'].html_name in self.data:
            return self.fields['current'].initial
        return self.cleaned_data['current']
