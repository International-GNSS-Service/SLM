"""
Handles forms for site log sections, user
management.

There is a form for each sitelog section.

More info on forms:
https://docs.djangoproject.com/en/stable/topics/forms/

More info on field types:
https://docs.djangoproject.com/en/stable/ref/models/fields/
"""

import json

from ckeditor.widgets import CKEditorWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms
from django.conf import settings
from django.contrib.gis.forms import PointField
from django.contrib.gis.geos import Point, Polygon
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from django.db.models import Max
from django.db.models.fields import NOT_PROVIDED
from django.forms.fields import BooleanField, CharField, TypedMultipleChoiceField
from django.forms.widgets import (
    CheckboxInput,
    CheckboxSelectMultiple,
    MultiWidget,
    NullBooleanSelect,
    NumberInput,
    Select,
    TextInput,
)
from django.urls import reverse_lazy
from django.utils.functional import Promise, SimpleLazyObject, cached_property
from django.utils.translation import gettext as _
from django_enum.choices import choices
from django_enum.forms import EnumChoiceField
from polyline import polyline

from slm.api.edit.serializers import UserProfileSerializer, UserSerializer
from slm.defines import (
    AlertLevel,
    CardinalDirection,
    CoordinateMode,
    FrequencyStandardType,
    ISOCountry,
    SiteLogStatus,
    SLMFileType,
)
from slm.models import (
    Agency,
    Alert,
    Antenna,
    Network,
    Radome,
    Receiver,
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
)
from slm.validators import FieldRequired, get_validators
from slm.widgets import (
    AutoComplete,
    AutoCompleteEnumSelectMultiple,
    AutoCompleteSelectMultiple,
    DatePicker,
    EnumSelectMultiple,
    GraphicTextarea,
    SLMCheckboxSelectMultiple,
    SLMDateTimeWidget,
)


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
        return {"on": "true", "off": "false"}.get(
            value.lower() if isinstance(value, str) else value,
            super().format_value(value),
        )

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if isinstance(value, list):
            value = value[0]
        return {"on": True, "off": False}.get(
            value.lower() if isinstance(value, str) else value,
            super().value_from_datadict(data, files, name),
        )


class SLMBooleanField(BooleanField):
    widget = SLMCheckboxInput

    def to_python(self, value):
        if isinstance(value, str) and value.lower() in ("false", "0", "off"):
            value = False
        else:
            value = bool(value)
        return super().to_python(value)


class SLMNullBooleanSelect(NullBooleanSelect):
    def __init__(self, attrs=None):
        choices = (
            ("", _("Unknown")),
            ("true", _("Yes")),
            ("false", _("No")),
        )
        # skip NullBooleanSelect init
        Select.__init__(self, attrs, choices)

    def format_value(self, value):
        if value in [None, "", "None"]:
            return [""]
        return [super().format_value(value)]

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        return {None: None, "": None}.get(
            value, super().value_from_datadict(data, files, name)
        )


class SiteAntennaGraphicField(CharField):
    widget = GraphicTextarea


class PolylineWidget(TextInput):
    def value_from_datadict(self, data, files, name):
        if hasattr(data, "getlist"):
            return data.getlist(name, []) or None
        return data.get(name, []) or None


class PolylineListField(forms.CharField):
    default_error_messages = {
        "invalid": _(
            "Unable to decode polyline {poly} - {error}. Bounding boxes "
            "should be line strings holding (longitude, latitude) tuples "
            "encoded using Google's polyline algorithm"
        )
    }

    widget = PolylineWidget

    def clean(self, value):
        if value is None or value == [""]:
            return None
        polygons = []
        for poly in value:
            try:
                linear_ring = polyline.decode(poly)
                linear_ring.append(linear_ring[0])  # close the ring
                polygons.append(Polygon(linear_ring))
            except Exception as exc:
                raise ValidationError(
                    self.error_messages["invalid"].format(poly=poly, error=str(exc)),
                    code="invalid",
                )
        return polygons


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
        return [super(EnumMultipleChoiceField, self).coerce(val) for val in value]


class SLMDateField(forms.DateField):
    input_type = "date"


class SLMTimeField(forms.TimeField):
    input_type = "time"


class SLMDateTimeField(forms.SplitDateTimeField):
    widget = SLMDateTimeWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.widgets[0].input_type = "date"
        self.widget.widgets[1].input_type = "time"


class PointWidget(MultiWidget):
    dim = 3

    template_name = "slm/forms/widgets/inline_multi.html"

    def __init__(self, dim=dim, attrs=None):
        self.dim = dim
        super().__init__([NumberInput(attrs=attrs) for _ in range(0, self.dim)], attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # fix the names so they are all the same
        for subwidget in context["widget"]["subwidgets"]:
            subwidget["name"] = "_".join(subwidget["name"].split("_")[:-1])
        return context

    def decompress(self, values):
        from django.contrib.gis.geos import Point

        if values is None:
            return Point(*[None for _ in range(0, self.dim)])
        return Point(*values)

    def value_from_datadict(self, data, files, name):
        if name in data:
            coords = []
            for coord in data.getlist(name):
                try:
                    coords.append(float(coord))
                except (ValueError, TypeError):
                    coords.append(coord)
            return coords
        return None


class SLMPointField(PointField):
    widget = PointWidget

    def __init__(self, *args, attrs=None, dim=None, **kwargs):
        if dim is not None:
            self.widget = self.widget(dim=dim)
        super().__init__(*args, **kwargs)
        if self.widget.attrs is None:
            self.widget.attrs = {}
        self.widget.attrs.update(attrs or {})

    def clean(self, value):
        """
        Raise a ValidationError if the value cannot be
        instantiated as a Point - otherwise return the Point or None.
        """
        if value is None:
            return value

        # Ensuring that the geometry is of the correct type (indicated
        # using the OGC string label).
        if len(value) != self.widget.dim:
            raise ValidationError(
                self.error_messages["invalid_geom_type"], code="invalid_geom_type"
            )
        try:
            return (
                Point(*[None if val in ["", None] else float(val) for val in value])
                or None
            )
        except (ValueError, TypeError) as err:
            raise ValidationError(
                self.error_messages["invalid_geom_type"], code="invalid_geom_type"
            ) from err


class AutoSelectMixin:
    def __init__(
        self,
        *args,
        value_param="id",
        label_param=None,
        render_suggestion=None,
        query_params=None,
        menu_class=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({"data-value-param": value_param})
        self.widget.attrs["data-value-param"] = value_param
        if label_param:
            self.widget.attrs["data-label-param"] = label_param
        if render_suggestion:
            self.widget.attrs["data-render-suggestion"] = render_suggestion
        if menu_class:
            self.widget.attrs["data-menu-class"] = menu_class
        if query_params:
            self.widget.attrs["data-query-params"] = (
                query_params
                if isinstance(query_params, str)
                else json.dumps(query_params)
            )
        self.widget.attrs["class"] = " ".join(
            [*self.widget.attrs.get("class", "").split(" "), "search-input"]
        )


class ModelAutoSelectMixin(AutoSelectMixin):
    def __init__(self, service_url, *args, search_param="search", **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs["data-service-url"] = service_url
        self.widget.attrs["data-search-param"] = search_param


class ModelAutoComplete(ModelAutoSelectMixin, forms.ModelChoiceField):
    widget = AutoComplete


class ModelMultipleAutoComplete(ModelAutoSelectMixin, forms.ModelMultipleChoiceField):
    widget = AutoCompleteSelectMultiple


class EnumAutoSelectMixin(AutoSelectMixin):
    class PropertyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Promise):
                return str(obj)
            return super().default(obj)

    def __init__(self, enum, *args, properties=None, data_source=None, **kwargs):
        super().__init__(
            enum,
            *args,
            value_param=kwargs.pop("value_param", "value"),
            label_param=kwargs.pop("label_param", "label"),
            **kwargs,
        )
        properties = set(properties or [])
        properties.update({"value", "label"})

        def lazy_source():
            """
            Data sources might hit the database - so we have to evaluate them
            lazily at widget render time instead of before django bootstrapping
            """
            return json.dumps(
                sorted(
                    [
                        {prop: getattr(en, prop) for prop in properties}
                        for en in (data_source() if data_source else enum or [])
                    ],
                    key=lambda en: en[self.widget.attrs["data-label-param"]],
                ),
                cls=MultiSelectEnumAutoComplete.PropertyEncoder,
            )

        self.widget.attrs["data-source"] = SimpleLazyObject(lazy_source)


class MultiSelectEnumAutoComplete(EnumAutoSelectMixin, EnumMultipleChoiceField):
    widget = AutoCompleteEnumSelectMultiple


class SelectEnumAutoComplete(EnumAutoSelectMixin, EnumChoiceField):
    widget = AutoComplete

    def __init__(self, *args, widget=AutoComplete, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


class NewSiteForm(forms.ModelForm):
    @property
    def helper(self):
        helper = FormHelper()
        helper.form_id = "slm-new-site-form"
        helper.layout = Layout(
            Div(
                Div("name", css_class="col-3"),
                Div("agencies", css_class="col-9"),
                css_class="row",
            )
        )
        return helper

    agencies = ModelMultipleAutoComplete(
        queryset=Agency.objects.all(),
        help_text=_("Enter the name or abbreviation of an Agency."),
        label=_("Agency"),
        required=False,
        service_url=reverse_lazy("slm_edit_api:agency-list"),
        search_param="search",
        value_param="id",
        label_param="name",
        render_suggestion="return `(${obj.shortname}) ${obj.name}`;",
    )

    class Meta:
        model = Site
        fields = ["name", "agencies"]


class SectionForm(forms.ModelForm):
    def __init__(self, instance=None, **kwargs):
        self.diff = instance.published_diff() if instance else {}
        self.flags = instance._flags if instance else {}
        super().__init__(instance=instance, **kwargs)
        for field in self.fields:
            try:
                model_field = self.Meta.model._meta.get_field(field)
                for validator in get_validators(self.Meta.model, model_field.name):
                    if isinstance(validator, FieldRequired):
                        self.fields[field].required = True
                        break
                self.fields[field].required |= not (
                    getattr(model_field, "default", None) != NOT_PROVIDED
                    and model_field.blank
                )
                self.fields[field].widget.attrs.setdefault("class", "")
                self.fields[field].widget.attrs["class"] += " slm-form-field"
            except FieldDoesNotExist:
                pass

    @classmethod
    def section_name(cls):
        return cls.Meta.model.section_name()

    @classmethod
    def section_slug(cls):
        return cls.Meta.model.section_slug()

    @property
    def num_flags(self):
        return len(self.flags)

    @classmethod
    def api(cls):
        return f"slm_edit_api:{cls.Meta.model.__name__.lower()}"

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
                if hasattr(getattr(self.Meta.model, field_name), "field"):
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
        queryset=Site.objects.all(), widget=forms.HiddenInput()
    )

    id = forms.IntegerField(
        validators=[MinValueValidator(0)], widget=forms.HiddenInput(), required=False
    )

    class Meta:
        fields = ["site", "id"]


class SubSectionForm(SectionForm):
    subsection = forms.IntegerField(
        validators=[MinValueValidator(0)], widget=forms.HiddenInput(), required=False
    )

    def save(self, commit=True):
        if self.instance.subsection is None:
            with transaction.atomic():
                # todo is there a race condition here?
                self.instance.subsection = (
                    self.Meta.model.objects.select_for_update()
                    .filter(site=self.instance.site)
                    .aggregate(Max("subsection"))["subsection__max"]
                    or 0
                ) + 1

                return super().save(commit=commit)
        return super().save(commit=commit)

    @classmethod
    def group_name(cls):
        if hasattr(cls, "NAV_HEADING"):
            return cls.NAV_HEADING.replace(" ", "_").replace(".", "").strip().lower()
        return None

    class Meta(SectionForm.Meta):
        fields = [*SectionForm.Meta.fields, "subsection"]


class SiteFormForm(SectionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ["report_type", "date_prepared"]:
            self.fields[field].required = False
            self.fields[field].widget.attrs["disabled"] = "disabled"

    # we only include this for legacy purposes - this is not an editable value
    previous_log = forms.CharField(
        label=_("Previous Site Log"),
        help_text=_(
            "Previous site log in this format: ssss_CCYYMMDD.log "
            "Format: (ssss = 4 character site name). If the site already has "
            "a log at the IGS Central Bureau it can be found at"
            "https://files.igs.org/pub/station/log/"
        ),
        disabled=True,
        required=False,
    )

    class Meta(SectionForm.Meta):
        model = SiteForm
        fields = [*SectionForm.Meta.fields, *SiteForm.site_log_fields(), "previous_log"]
        widgets = {"date_prepared": DatePicker}


class SiteIdentificationForm(SectionForm):
    # we only include this for legacy purposes - this is not an editable value
    nine_character_id = forms.CharField(
        label=_("Nine Character ID"),
        help_text=_(
            "This is the 9 Character station name (XXXXMRCCC) used in RINEX 3 "
            "filenames. Format: (XXXX - existing four character IGS station "
            "name, M - Monument or marker number (0-9), R - Receiver number "
            "(0-9), CCC - Three digit ISO 3166-1 country code)"
        ),
        disabled=True,
        required=False,
    )

    class Meta(SectionForm.Meta):
        model = SiteIdentification
        fields = [
            *SectionForm.Meta.fields,
            *SiteIdentification.site_log_fields(),
            "nine_character_id",
        ]
        field_classes = {"date_installed": SLMDateTimeField}


class SiteLocationForm(SectionForm):
    country = SelectEnumAutoComplete(
        ISOCountry,
        help_text=SiteLocation._meta.get_field("country").help_text,
        label=SiteLocation._meta.get_field("country").verbose_name,
        render_suggestion=(
            'return `<span class="fi fi-${obj.value.toLowerCase()}"></span>'
            '<span class="matchable">${obj.label}</span>`;'
        ),
        strict=False,
    )

    xyz = SLMPointField(
        help_text=SiteLocation._meta.get_field("xyz").help_text,
        label=SiteLocation._meta.get_field("xyz").verbose_name,
        disabled=getattr(settings, "SLM_COORDINATE_MODE", CoordinateMode.INDEPENDENT)
        == CoordinateMode.LLH,
    )

    llh = SLMPointField(
        help_text=SiteLocation._meta.get_field("llh").help_text,
        label=SiteLocation._meta.get_field("llh").verbose_name,
        attrs={"step": 0.0000001},
        disabled=getattr(settings, "SLM_COORDINATE_MODE", CoordinateMode.INDEPENDENT)
        == CoordinateMode.ECEF,
    )

    class Meta:
        model = SiteLocation
        fields = [*SectionForm.Meta.fields, *SiteLocation.site_log_fields()]


class SiteReceiverForm(SubSectionForm):
    COPY_LAST_ON_ADD = [
        field
        for field in [*SubSectionForm.Meta.fields, *SiteReceiver.site_log_fields()]
        if field not in {"installed", "removed", "additional_info"}
    ]

    satellite_system = forms.ModelChoiceField(
        queryset=SatelliteSystem.objects.all(),
        help_text=SiteReceiver._meta.get_field("satellite_system").help_text,
        label=SiteReceiver._meta.get_field("satellite_system").verbose_name,
        required=True,
        widget=SLMCheckboxSelectMultiple(columns=4),
        empty_label=None,
    )

    receiver_type = ModelAutoComplete(
        queryset=Receiver.objects.all(),
        service_url=reverse_lazy("slm_public_api:receiver-list"),
        help_text=SiteReceiver._meta.get_field("receiver_type").help_text,
        label=SiteReceiver._meta.get_field("receiver_type").verbose_name,
        search_param="model",
        value_param="model",
        label_param="model",
        to_field_name="model",
    )

    temp_stabilized = forms.NullBooleanField(
        help_text=SiteReceiver._meta.get_field("temp_stabilized").help_text,
        label=SiteReceiver._meta.get_field("temp_stabilized").verbose_name,
        widget=SLMNullBooleanSelect(),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # todo why is this not automatically done?
        if "satellite_system" in self.initial:
            self.initial["satellite_system"] = [
                system.name for system in self.initial["satellite_system"].all()
            ]

    class Meta(SubSectionForm):
        model = SiteReceiver
        fields = [*SubSectionForm.Meta.fields, *SiteReceiver.site_log_fields()]
        field_classes = {"installed": SLMDateTimeField, "removed": SLMDateTimeField}


class SiteAntennaForm(SubSectionForm):
    COPY_LAST_ON_ADD = [
        field
        for field in [*SubSectionForm.Meta.fields, *SiteAntenna.site_log_fields()]
        if field not in {"installed", "removed", "additional_info"}
    ]

    marker_une = SLMPointField(
        help_text=SiteAntenna._meta.get_field("marker_une").help_text,
        label=SiteAntenna._meta.get_field("marker_une").verbose_name,
    )

    alignment = forms.FloatField(
        required=SiteAntenna._meta.get_field("alignment").blank,
        help_text=SiteAntenna._meta.get_field("alignment").help_text,
        label=SiteAntenna._meta.get_field("alignment").verbose_name,
        max_value=180,
        min_value=-180,
    )

    antenna_type = ModelAutoComplete(
        queryset=Antenna.objects.all(),
        service_url=reverse_lazy("slm_public_api:antenna-list"),
        help_text=SiteAntenna._meta.get_field("antenna_type").help_text,
        label=SiteAntenna._meta.get_field("antenna_type").verbose_name,
        search_param="model",
        value_param="model",
        label_param="model",
        to_field_name="model",
    )

    radome_type = ModelAutoComplete(
        queryset=Radome.objects.all(),
        service_url=reverse_lazy("slm_public_api:radome-list"),
        help_text=SiteAntenna._meta.get_field("radome_type").help_text,
        label=SiteAntenna._meta.get_field("radome_type").verbose_name,
        search_param="model",
        value_param="model",
        label_param="model",
        to_field_name="model",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance exists (i.e., it's an edit form, not a new form)
        if self.instance and self.instance.pk:
            self.fields["custom_graphic"].initial = self.instance.graphic

    class Meta(SubSectionForm):
        model = SiteAntenna
        fields = [*SubSectionForm.Meta.fields, *SiteAntenna.site_log_fields()]
        field_classes = {
            "installed": SLMDateTimeField,
            "removed": SLMDateTimeField,
            "custom_graphic": SiteAntennaGraphicField,
        }


class SiteSurveyedLocalTiesForm(SubSectionForm):
    diff_xyz = SLMPointField(
        help_text=SiteSurveyedLocalTies._meta.get_field("diff_xyz").help_text,
        label=SiteSurveyedLocalTies._meta.get_field("diff_xyz").verbose_name,
    )

    class Meta(SubSectionForm.Meta):
        model = SiteSurveyedLocalTies
        fields = [*SubSectionForm.Meta.fields, *SiteSurveyedLocalTies.site_log_fields()]
        field_classes = {"measured": SLMDateTimeField, "diff_xyz": SLMPointField}


class SiteFrequencyStandardForm(SubSectionForm):
    class Meta(SubSectionForm.Meta):
        model = SiteFrequencyStandard
        fields = [*SubSectionForm.Meta.fields, *SiteFrequencyStandard.site_log_fields()]
        widgets = {"effective_start": DatePicker, "effective_end": DatePicker}


class SiteCollocationForm(SubSectionForm):
    class Meta(SubSectionForm.Meta):
        model = SiteCollocation
        fields = [*SubSectionForm.Meta.fields, *SiteCollocation.site_log_fields()]
        widgets = {"effective_start": DatePicker, "effective_end": DatePicker}


class MeteorologicalForm(SubSectionForm):
    NAV_HEADING = _("Meteorological Instr.")

    class Meta(SubSectionForm):
        fields = SubSectionForm.Meta.fields
        widgets = {
            "calibration": DatePicker,
            "effective_start": DatePicker,
            "effective_end": DatePicker,
        }


class SiteHumiditySensorForm(MeteorologicalForm):
    class Meta(MeteorologicalForm.Meta):
        model = SiteHumiditySensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteHumiditySensor.site_log_fields(),
        ]


class SitePressureSensorForm(MeteorologicalForm):
    class Meta(MeteorologicalForm.Meta):
        model = SitePressureSensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SitePressureSensor.site_log_fields(),
        ]


class SiteTemperatureSensorForm(MeteorologicalForm):
    class Meta(MeteorologicalForm.Meta):
        model = SiteTemperatureSensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteTemperatureSensor.site_log_fields(),
        ]


class SiteWaterVaporRadiometerForm(MeteorologicalForm):
    class Meta(MeteorologicalForm.Meta):
        model = SiteWaterVaporRadiometer
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteWaterVaporRadiometer.site_log_fields(),
        ]


class SiteOtherInstrumentationForm(MeteorologicalForm):
    class Meta(MeteorologicalForm.Meta):
        model = SiteOtherInstrumentation
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteOtherInstrumentation.site_log_fields(),
        ]


class LocalConditionForm(SubSectionForm):
    NAV_HEADING = _("Local Conditions")

    class Meta(SubSectionForm.Meta):
        fields = SubSectionForm.Meta.fields
        widgets = {"effective_start": DatePicker, "effective_end": DatePicker}


class SiteRadioInterferencesForm(LocalConditionForm):
    class Meta(LocalConditionForm.Meta):
        model = SiteRadioInterferences
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteRadioInterferences.site_log_fields(),
        ]


class SiteMultiPathSourcesForm(LocalConditionForm):
    class Meta(LocalConditionForm.Meta):
        model = SiteMultiPathSources
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteMultiPathSources.site_log_fields(),
        ]


class SiteSignalObstructionsForm(LocalConditionForm):
    class Meta(LocalConditionForm.Meta):
        model = SiteSignalObstructions
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteSignalObstructions.site_log_fields(),
        ]


class SiteLocalEpisodicEffectsForm(SubSectionForm):
    class Meta(SubSectionForm.Meta):
        model = SiteLocalEpisodicEffects
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteLocalEpisodicEffects.site_log_fields(),
        ]
        widgets = {"effective_start": DatePicker, "effective_end": DatePicker}


class AgencyPOCForm(SectionForm):
    class Meta(SectionForm.Meta):
        fields = SectionForm.Meta.fields
        widgets = {
            "agency": forms.Textarea(attrs={"rows": 2}),
            "mailing_address": forms.Textarea(attrs={"rows": 4}),
        }


class SiteOperationalContactForm(AgencyPOCForm):
    class Meta(AgencyPOCForm.Meta):
        model = SiteOperationalContact
        fields = [*AgencyPOCForm.Meta.fields, *SiteOperationalContact.site_log_fields()]


class SiteResponsibleAgencyForm(AgencyPOCForm):
    class Meta(AgencyPOCForm.Meta):
        model = SiteResponsibleAgency
        fields = [*AgencyPOCForm.Meta.fields, *SiteResponsibleAgency.site_log_fields()]


class SiteMoreInformationForm(SectionForm):
    class Meta(SectionForm.Meta):
        model = SiteMoreInformation
        fields = [*SectionForm.Meta.fields, *SiteMoreInformation.site_log_fields()]


class UserForm(forms.ModelForm):
    @property
    def helper(self):
        helper = FormHelper()
        helper.form_id = "slm-user-form"
        helper.layout = Layout(
            Div(Div("email"), css_class="row"),
            Div(
                Div("first_name", css_class="col-6"),
                Div("last_name", css_class="col-6"),
                css_class="row",
            ),
            Div(
                Div("silence_alerts", css_class="col-6"),
                Div("html_emails", css_class="col-6"),
                css_class="row",
            ),
            Div(Div("agencies"), css_class="row"),
        )
        return helper

    agencies = forms.ModelMultipleChoiceField(
        queryset=Agency.objects.all(), required=False, disabled=True
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        if instance:
            self.fields["agencies"].queryset = instance.agencies.all()

    class Meta:
        model = UserSerializer.Meta.model
        fields = UserSerializer.Meta.fields
        exclude = ("date_joined", "profile")


class UserProfileForm(forms.ModelForm):
    @property
    def helper(self):
        helper = FormHelper()
        helper.form_id = "slm-user-profile-form"
        helper.layout = Layout(
            Div(
                Div("phone1", css_class="col-6"),
                Div("phone2", css_class="col-6"),
                css_class="row",
            ),
            Div(Div("address1"), css_class="row"),
            Div(Div("address2"), css_class="row"),
            Div(Div("address3"), css_class="row"),
            Div(
                Div("city", css_class="col-6"),
                Div("state_province", css_class="col-6"),
                css_class="row",
            ),
            Div(
                Div("country", css_class="col-6"),
                Div("postal_code", css_class="col-6"),
                css_class="row",
            ),
        )
        return helper

    class Meta:
        model = UserProfileSerializer.Meta.model
        fields = UserProfileSerializer.Meta.fields
        exclude = ("registration_agency",)


class SiteFileForm(forms.ModelForm):
    name = forms.SlugField(max_length=255, help_text=_("The name of the file."))

    direction = EnumChoiceField(
        CardinalDirection,
        help_text=SiteFileUpload._meta.get_field("direction").help_text,
        label=SiteFileUpload._meta.get_field("direction").verbose_name,
        choices=[("", "-" * 10), *choices(CardinalDirection)],
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        if instance and instance.file_type != SLMFileType.SITE_IMAGE:
            self.fields["direction"].widget = forms.HiddenInput()
            self.fields["direction"].disabled = True

    class Meta:
        model = SiteFileUpload
        fields = ["name", "description", "direction"]


class RichTextForm(forms.Form):
    text = forms.CharField(widget=CKEditorWidget(config_name="richtextinput"))


class StationFilterForm(forms.Form):
    name = forms.CharField(required=False)

    status = EnumMultipleChoiceField(
        SiteLogStatus,
        # help_text=_('Include stations with these statuses.'),
        label=_("Site Status"),
        required=False,
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
        label=_("Alert Level"),
        required=False,
    )

    station = ModelMultipleAutoComplete(
        queryset=Site.objects.public(),
        service_url=reverse_lazy("slm_public_api:name-list"),
        # help_text=Site._meta.get_field('name').help_text,
        # label=Site._meta.get_field('name').verbose_name,
        search_param="name",
        value_param="name",
        label_param="name",
        menu_class="station-names",
        to_field_name="name",
        required=False,
    )

    satellite_system = forms.ModelMultipleChoiceField(
        queryset=SatelliteSystem.objects.all(),
        label=SiteReceiver._meta.get_field("satellite_system").verbose_name,
        required=False,
        widget=CheckboxSelectMultiple(),
    )

    frequency_standard = EnumMultipleChoiceField(
        FrequencyStandardType, required=False, label=_("Frequency Standard")
    )

    current = SLMBooleanField(
        label=_("Current"),
        help_text=_("Only include sites that currently have this equipment."),
        initial=True,
        required=False,
    )

    receiver = ModelMultipleAutoComplete(
        queryset=Receiver.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_("Receiver"),
        required=False,
        service_url=reverse_lazy("slm_public_api:receiver-list"),
        search_param="model",
        value_param="id",
        label_param="model",
        query_params={"in_use": True},
    )

    antenna = ModelMultipleAutoComplete(
        queryset=Antenna.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_("Antenna"),
        required=False,
        service_url=reverse_lazy("slm_public_api:antenna-list"),
        search_param="model",
        value_param="id",
        label_param="model",
        query_params={"in_use": True},
    )

    radome = ModelMultipleAutoComplete(
        queryset=Radome.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_("Radome"),
        required=False,
        service_url=reverse_lazy("slm_public_api:radome-list"),
        search_param="model",
        value_param="id",
        label_param="model",
        query_params={"in_use": True},
    )

    agency = ModelMultipleAutoComplete(
        queryset=Agency.objects.all(),
        # help_text=_('Enter the name or abbreviation of an Agency.'),
        label=_("Agency"),
        required=False,
        service_url=reverse_lazy("slm_edit_api:agency-list"),
        search_param="search",
        value_param="id",
        label_param="name",
        render_suggestion=(
            'return `<span class="matchable">(${obj.shortname})</span>'
            '<span class="matchable">${obj.name}</span>`;'
        ),
    )

    network = ModelMultipleAutoComplete(
        queryset=Network.objects.all(),
        # help_text=_('Enter the name of an IGS Network.'),
        label=_("Network"),
        required=False,
        service_url=reverse_lazy("slm_edit_api:network-list"),
        search_param="name",
        value_param="id",
        label_param="name",
    )

    country = MultiSelectEnumAutoComplete(
        # help_text=_('Enter the name of a country or region.'),
        ISOCountry,
        label=_("Country/Region"),
        required=False,
        render_suggestion=(
            'return `<span class="fi fi-${obj.value.toLowerCase()}"></span>'
            '<span class="matchable">${obj.label}</span>`;'
        ),
        data_source=ISOCountry.with_stations,
    )

    geography = PolylineListField(
        required=False,
        label=_("Geographic Bounds"),
        help_text=_(
            "Bounding boxes should be line strings holding (longitude, "
            "latitude) tuples encoded using Google's polyline algorithm."
        ),
    )

    def clean_current(self):
        # todo mixin that does this
        if self["current"].html_name not in self.data:
            return self.fields["current"].initial
        return self.cleaned_data["current"]
