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
from slm.utils import to_snake_case
from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from slm.models import (
    Site,
    SiteForm,
    SiteIdentification,
    SiteLocation,
    SiteReceiver,
    SiteAntenna,
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
    SatelliteSystem
)
from django.urls import reverse
from django.db import transaction
from django.db.models import Max
from django.core.validators import MinValueValidator
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.utils.functional import cached_property


class UserAdminCreationForm(forms.ModelForm):
    # Creates new users with all the required
    # fields. Requires repeated password.

    password = forms.CharField(widget=forms.PasswordInput)
    password_2 = forms.CharField(label='Confirm Password',
                                 widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = ['email']

    def clean(self):
        # Verify both passwords match.

        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_2 = cleaned_data.get("password_2")
        if password is not None and password != password_2:
            self.add_error("password_2", "Your passwords must match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserAdminChangeForm(forms.ModelForm):
    """
    Updates users. Replaces password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = get_user_model()
        fields = ['email', 'password', 'is_active', 'is_superuser']

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class NewSiteForm(forms.ModelForm):

    class Meta:
        model = Site
        fields = ['name', 'agencies']


class SectionForm(forms.ModelForm):

    def __init__(self, instance=None, **kwargs):
        self.diff = instance.published_diff() if instance else {}
        self.flags = instance._flags if instance else {}
        super().__init__(instance=instance, **kwargs)

    @classmethod
    def section_name(cls):
        #return self.Meta.model.section_name
        return to_snake_case(cls.Meta.model.__name__).replace('_', ' ').replace('site', '').title().strip()

    @property
    def num_flags(self):
        return len(self.flags)

    @classmethod
    def api(cls):
        return f'slm_edit_api:{cls.Meta.model.__name__.lower()}'

    @cached_property
    def structured_fields(self):
        # todo this is spaghetti
        # arrange fields in structure to easily produce fieldsets in correct order in the template, reflects old site
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

            return [self.fields[field].get_bound_field(form=self, field_name=field) for field in fields]

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

    site = forms.ModelChoiceField(
        queryset=Site.objects.all(),  # todo this might be a security hole - restrict queryset to user's stations
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
                self.instance.subsection = (self.Meta.model.objects.select_for_update().filter(
                    site=self.instance.site
                ).aggregate(Max('subsection'))['subsection__max'] or 0) + 1

                return super().save(commit=commit)
        return super().save(commit=commit)


    class Meta:
        fields = SectionForm.Meta.fields + ['subsection']


class SiteFormForm(SectionForm):

    class Meta:
        model = SiteForm
        fields = SectionForm.Meta.fields + SiteForm.site_log_fields()


class SiteIdentificationForm(SectionForm):

    class Meta:
        model = SiteIdentification
        fields = SectionForm.Meta.fields + SiteIdentification.site_log_fields()


class SiteLocationForm(SectionForm):

    class Meta:
        model = SiteLocation
        fields = SectionForm.Meta.fields + SiteLocation.site_log_fields()


class SiteReceiverForm(SubSectionForm):

    satellite_system = forms.ModelChoiceField(
        queryset=SatelliteSystem.objects.all(),
        help_text=SiteReceiver._meta.get_field('satellite_system').help_text,
        label=SiteReceiver._meta.get_field('satellite_system').verbose_name,
        widget=forms.SelectMultiple
    )

    elevation_cutoff = forms.FloatField(
        required=SiteReceiver._meta.get_field('elevation_cutoff').blank,
        help_text=SiteReceiver._meta.get_field('elevation_cutoff').help_text,
        label=SiteReceiver._meta.get_field('elevation_cutoff').verbose_name,
        max_value=15,
        min_value=-5
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

    class Meta:
        model = SiteReceiver
        fields = SubSectionForm.Meta.fields + SiteReceiver.site_log_fields()


class SiteAntennaForm(SubSectionForm):

    alignment = forms.FloatField(
        required=SiteAntenna._meta.get_field('alignment').blank,
        help_text=SiteAntenna._meta.get_field('alignment').help_text,
        label=SiteAntenna._meta.get_field('alignment').verbose_name,
        max_value=180,
        min_value=-180
    )

    class Meta:
        model = SiteAntenna
        fields = SubSectionForm.Meta.fields + SiteAntenna.site_log_fields()


class SiteSurveyedLocalTiesForm(SubSectionForm):

    accuracy = forms.FloatField(
        required=SiteSurveyedLocalTies._meta.get_field('accuracy').blank,
        help_text=SiteSurveyedLocalTies._meta.get_field('accuracy').help_text,
        label=SiteSurveyedLocalTies._meta.get_field('accuracy').verbose_name
    )

    class Meta:
        model = SiteSurveyedLocalTies
        fields = SubSectionForm.Meta.fields + SiteSurveyedLocalTies.site_log_fields()


class SiteFrequencyStandardForm(SubSectionForm):

    input_frequency = forms.FloatField(
        required=SiteFrequencyStandard._meta.get_field('input_frequency').blank,
        help_text=SiteFrequencyStandard._meta.get_field('input_frequency').help_text,
        label=SiteFrequencyStandard._meta.get_field('input_frequency').verbose_name
    )

    class Meta:
        model = SiteFrequencyStandard
        fields = SubSectionForm.Meta.fields + SiteFrequencyStandard.site_log_fields()


class SiteCollocationForm(SubSectionForm):

    class Meta:
        model = SiteCollocation
        fields = SubSectionForm.Meta.fields + SiteCollocation.site_log_fields()


class MeteorologicalForm(SubSectionForm):

    NAV_HEADING = _('Meteorological Instr.')


class SiteHumiditySensorForm(MeteorologicalForm):

    accuracy = forms.FloatField(
        required=SiteHumiditySensor._meta.get_field('accuracy').blank,
        help_text=SiteHumiditySensor._meta.get_field('accuracy').help_text,
        label=SiteHumiditySensor._meta.get_field('accuracy').verbose_name
    )

    sampling_interval = forms.FloatField(
        required=SiteHumiditySensor._meta.get_field('sampling_interval').blank,
        help_text=SiteHumiditySensor._meta.get_field('sampling_interval').help_text,
        label=SiteHumiditySensor._meta.get_field('sampling_interval').verbose_name
    )

    class Meta:
        model = SiteHumiditySensor
        fields = MeteorologicalForm.Meta.fields + SiteHumiditySensor.site_log_fields()


class SitePressureSensorForm(MeteorologicalForm):

    accuracy = forms.FloatField(
        required=SitePressureSensor._meta.get_field('accuracy').blank,
        help_text=SitePressureSensor._meta.get_field('accuracy').help_text,
        label=SitePressureSensor._meta.get_field('accuracy').verbose_name
    )

    sampling_interval = forms.FloatField(
        required=SitePressureSensor._meta.get_field('sampling_interval').blank,
        help_text=SitePressureSensor._meta.get_field('sampling_interval').help_text,
        label=SitePressureSensor._meta.get_field('sampling_interval').verbose_name
    )

    class Meta:
        model = SitePressureSensor
        fields = MeteorologicalForm.Meta.fields + SitePressureSensor.site_log_fields()


class SiteTemperatureSensorForm(MeteorologicalForm):

    accuracy = forms.FloatField(
        required=SiteTemperatureSensor._meta.get_field('accuracy').blank,
        help_text=SiteTemperatureSensor._meta.get_field('accuracy').help_text,
        label=SiteTemperatureSensor._meta.get_field('accuracy').verbose_name
    )

    sampling_interval = forms.FloatField(
        required=SiteTemperatureSensor._meta.get_field('sampling_interval').blank,
        help_text=SiteTemperatureSensor._meta.get_field(
            'sampling_interval').help_text,
        label=SiteTemperatureSensor._meta.get_field(
            'sampling_interval').verbose_name
    )

    class Meta:
        model = SiteTemperatureSensor
        fields = MeteorologicalForm.Meta.fields + SiteTemperatureSensor.site_log_fields()


class SiteWaterVaporRadiometerForm(MeteorologicalForm):

    class Meta:
        model = SiteWaterVaporRadiometer
        fields = MeteorologicalForm.Meta.fields + SiteWaterVaporRadiometer.site_log_fields()


class SiteOtherInstrumentationForm(MeteorologicalForm):

    class Meta:
        model = SiteOtherInstrumentation
        fields = MeteorologicalForm.Meta.fields + SiteOtherInstrumentation.site_log_fields()


class LocalConditionForm(SubSectionForm):

    NAV_HEADING = _('Local Conditions')


class SiteRadioInterferencesForm(LocalConditionForm):

    class Meta:
        model = SiteRadioInterferences
        fields = LocalConditionForm.Meta.fields + SiteRadioInterferences.site_log_fields()


class SiteMultiPathSourcesForm(LocalConditionForm):

    class Meta:
        model = SiteMultiPathSources
        fields = LocalConditionForm.Meta.fields + SiteMultiPathSources.site_log_fields()


class SiteSignalObstructionsForm(LocalConditionForm):

    class Meta:
        model = SiteSignalObstructions
        fields = LocalConditionForm.Meta.fields + SiteSignalObstructions.site_log_fields()


class SiteLocalEpisodicEffectsForm(SubSectionForm):

    class Meta:
        model = SiteLocalEpisodicEffects
        fields = SubSectionForm.Meta.fields + SiteLocalEpisodicEffects.site_log_fields()


class SiteOperationalContactForm(SectionForm):

    class Meta:
        model = SiteOperationalContact
        fields = SectionForm.Meta.fields + SiteOperationalContact.site_log_fields()


class SiteResponsibleAgencyForm(SectionForm):

    class Meta:
        model = SiteResponsibleAgency
        fields = SectionForm.Meta.fields + SiteResponsibleAgency.site_log_fields()


class SiteMoreInformationForm(SectionForm):

    class Meta:
        model = SiteMoreInformation
        fields = SectionForm.Meta.fields + SiteMoreInformation.site_log_fields()


class UserForm(forms.ModelForm):

    agency = forms.ModelChoiceField(
        queryset=Agency.objects.all(),  # todo this might be a security hole - restrict queryset to user's stations
        required=False,
        disabled=True
    )

    class Meta:
        model = get_user_model()
        fields = [
            'first_name',
            'last_name',
            'email',
            'agency'
        ]


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = [
            'phone1',
            'phone2',
            'address1',
            'address2',
            'address3',
            'city',
            'state_province',
            'country',
            'postal_code',
            'registration_agency',
            #'html_emails'  todo not rendering right
        ]
