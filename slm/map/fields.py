from django.db.models import CharField
from slm.map.defines import (
    MapBoxStyle,
    MapBoxProjection
)
from django.forms.fields import ChoiceField


class StyleChoiceField(ChoiceField):

    def to_python(self, value):
        """Return a string."""
        if value in self.empty_values:
            return ''
        return MapBoxStyle(str(value)).value

    def valid_value(self, value):
        """Check to see if the provided value is a valid choice."""
        try:
            return super().valid_value(MapBoxStyle(str(value)))
        except ValueError:
            return super().valid_value(value)


class MapBoxStyleField(CharField):

    choices_form_class = StyleChoiceField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            max_length=kwargs.pop('max_length', max([len(style.value) for style in MapBoxStyle])),
            choices=kwargs.pop('choices', MapBoxStyle.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return value
        if not value:
            value = self.default
        return MapBoxStyle(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return MapBoxStyle(value)

    def to_python(self, value):
        if isinstance(value, MapBoxStyle):
            return value

        if value is None:
            return value

        return MapBoxStyle(value)


class MapBoxProjectionChoiceField(ChoiceField):

    def to_python(self, value):
        """Return a string."""
        if value in self.empty_values:
            return ''
        return MapBoxProjection(str(value)).value

    def valid_value(self, value):
        """Check to see if the provided value is a valid choice."""
        try:
            return super().valid_value(MapBoxProjection(str(value)))
        except ValueError:
            return super().valid_value(value)


class MapBoxProjectionField(CharField):

    choices_form_class = StyleChoiceField

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            max_length=kwargs.pop('max_length', max([len(style.value) for style in MapBoxProjection])),
            choices=kwargs.pop('choices', MapBoxProjection.choices),
            **kwargs
        )

    def get_prep_value(self, value):
        if value is None:
            return value
        if not value:
            value = self.default
        return MapBoxProjection(value).value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return MapBoxProjection(value)

    def to_python(self, value):
        if isinstance(value, MapBoxProjection):
            return value

        if value is None:
            return value

        return MapBoxProjection(value)
