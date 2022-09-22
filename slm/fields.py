"""
TODO delete this file after migration squashing
"""

from django.db import models
from django.forms.fields import ChoiceField
from slm.defines import (
    EquipmentState,
    EquipmentType,
    Instrumentation,
    SatelliteSystem,
    TectonicPlates,
    SiteLogStatus,
    LogEntryType,
    AntennaReferencePoint,
    AntennaFeatures,
    AlertLevel
)


class EquipmentStateFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return EquipmentState(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(EquipmentState(value))
        except ValueError:
            return super(). valid_value(value)


class EquipmentStateField(models.PositiveSmallIntegerField):

    choices_form_class = EquipmentStateFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', EquipmentState.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return EquipmentState(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return EquipmentState(value)

    def to_python(self, value):
        if isinstance(value, EquipmentState):
            return value

        if value is None:
            return value

        return EquipmentState(value)


class EquipmentTypeFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return EquipmentType(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(EquipmentType(value))
        except ValueError:
            return super().valid_value(value)


class EquipmentTypeField(models.PositiveSmallIntegerField):
    choices_form_class = EquipmentTypeFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', EquipmentType.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return EquipmentType(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return EquipmentType(value)

    def to_python(self, value):
        if isinstance(value, EquipmentType):
            return value

        if value is None:
            return value

        return EquipmentType(value)


class InstrumentationFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return Instrumentation(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(Instrumentation(value))
        except ValueError:
            return super().valid_value(value)


class InstrumentationField(models.PositiveSmallIntegerField):
    choices_form_class = InstrumentationFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', Instrumentation.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return Instrumentation(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return Instrumentation(value)

    def to_python(self, value):
        if isinstance(value, Instrumentation):
            return value

        if value is None:
            return value

        return Instrumentation(value)


class SatelliteSystemFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return SatelliteSystem(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(SatelliteSystem(value))
        except ValueError:
            return super().valid_value(value)


class SatelliteSystemField(models.PositiveSmallIntegerField):
    choices_form_class = SatelliteSystemFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', SatelliteSystem.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return SatelliteSystem(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return SatelliteSystem(value)

    def to_python(self, value):
        if isinstance(value, SatelliteSystem):
            return value

        if value is None:
            return value

        return SatelliteSystem(value)


class TectonicPlatesFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return TectonicPlates(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(TectonicPlates(value))
        except ValueError:
            return super().valid_value(value)


class TectonicPlatesField(models.PositiveSmallIntegerField):
    choices_form_class = TectonicPlatesFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', TectonicPlates.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return TectonicPlates(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return TectonicPlates(value)

    def to_python(self, value):
        if isinstance(value, TectonicPlates):
            return value

        if value is None:
            return value

        return TectonicPlates(value)


class SiteLogStatusFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return SiteLogStatus(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(SiteLogStatus(value))
        except ValueError:
            return super().valid_value(value)


class AlertLevelFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return AlertLevel(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(AlertLevel(value))
        except ValueError:
            return super().valid_value(value)


class LogEntryTypeFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return LogEntryType(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(LogEntryType(value))
        except ValueError:
            return super().valid_value(value)


class SiteLogStatusField(models.PositiveSmallIntegerField):

    choices_form_class = SiteLogStatusFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', SiteLogStatus.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default.value
        return SiteLogStatus(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return SiteLogStatus(value)

    def to_python(self, value):
        if isinstance(value, SiteLogStatus):
            return value

        if value is None:
            return value

        return SiteLogStatus(value)


class AlertLevelField(models.PositiveSmallIntegerField):

    choices_form_class = AlertLevelFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', AlertLevel.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default.value
        return AlertLevel(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return AlertLevel(value)

    def to_python(self, value):
        if isinstance(value, AlertLevel):
            return value

        if value is None:
            return value

        return AlertLevel(value)


class LogEntryTypeField(models.PositiveSmallIntegerField):

    choices_form_class = LogEntryTypeFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', LogEntryType.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return LogEntryType(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return LogEntryType(value)

    def to_python(self, value):
        if isinstance(value, LogEntryType):
            return value

        if value is None:
            return value

        return LogEntryType(value)


class AntennaReferencePointFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return AntennaReferencePoint(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(AntennaReferencePoint(value))
        except ValueError:
            return super().valid_value(value)


class AntennaReferencePointField(models.PositiveSmallIntegerField):

    choices_form_class = AntennaReferencePointFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', AntennaReferencePoint.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return AntennaReferencePoint(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return AntennaReferencePoint(value)

    def to_python(self, value):
        if isinstance(value, AntennaReferencePoint):
            return value

        if value is None:
            return value

        return AntennaReferencePoint(value)


class AntennaFeaturesFormField(ChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            if value in self.empty_values:
                return ''
            return AntennaFeatures(value).value

    def valid_value(self, value):
        try:
            return super().valid_value(AntennaFeatures(value))
        except ValueError:
            return super().valid_value(value)


class AntennaFeaturesField(models.PositiveSmallIntegerField):

    choices_form_class = AntennaFeaturesFormField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=kwargs.pop('choices', AntennaFeatures.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return self.default
        return AntennaFeatures(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.default
        return AntennaFeatures(value)

    def to_python(self, value):
        if isinstance(value, AntennaFeatures):
            return value

        if value is None:
            return value

        return AntennaFeatures(value)
