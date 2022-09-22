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
from slm.models import (
    Site,
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
    Agency
)
from django.urls import reverse
from django.db import transaction
from django.db.models import Max
from django.core.validators import MinValueValidator
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.utils.functional import cached_property


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

    class Meta:
        model = SiteReceiver
        fields = SubSectionForm.Meta.fields + SiteReceiver.site_log_fields()


class SiteAntennaForm(SubSectionForm):

    class Meta:
        model = SiteAntenna
        fields = SubSectionForm.Meta.fields + SiteAntenna.site_log_fields()


class AntennaTypeForm(SectionForm):

    @classmethod
    def section_name(cls):
        return 'Antenna Type'

    class Meta:
        model = AntennaType
        fields = ['name', 'description', 'graphic']


class SiteSurveyedLocalTiesForm(SubSectionForm):

    class Meta:
        model = SiteSurveyedLocalTies
        fields = SubSectionForm.Meta.fields + SiteSurveyedLocalTies.site_log_fields()


class SiteFrequencyStandardForm(SubSectionForm):

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

    class Meta:
        model = SiteHumiditySensor
        fields = MeteorologicalForm.Meta.fields + SiteHumiditySensor.site_log_fields()


class SitePressureSensorForm(MeteorologicalForm):

    class Meta:
        model = SitePressureSensor
        fields = MeteorologicalForm.Meta.fields + SitePressureSensor.site_log_fields()


class SiteTemperatureSensorForm(MeteorologicalForm):

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
