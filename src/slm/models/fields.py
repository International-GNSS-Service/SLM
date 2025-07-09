# upstream/fields.py
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class StationNameField(models.CharField):
    """
    The StationNameField allows validation and help text to be configured in settings.
    These values will not be deconstructed into the migration files allowing users of
    the SLM to define their own semantics and validation logic around station names.
    """

    class StationNameValidator(RegexValidator):
        pass

    def __init__(self, *args, **kwargs):
        if regex := getattr(settings, "SLM_STATION_NAME_REGEX", None):
            kwargs.setdefault("validators", [])
            kwargs["validators"].append(self.StationNameValidator(regex))
        self._help_text = kwargs.pop("help_text", None)
        help_text = getattr(settings, "SLM_STATION_NAME_HELP", self._help_text)
        if help_text:
            kwargs["help_text"] = help_text
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Ensure the regex pattern doesn't get serialized if it came from settings
        validators = [
            validator
            for validator in kwargs.pop("validators", [])
            if not isinstance(validator, self.StationNameValidator)
        ]
        if validators:
            kwargs["validators"] = validators

        # we want the cannonical help text to be used in migration files
        if self._help_text is not None:
            kwargs["help_text"] = self._help_text
        return name, path, args, kwargs
