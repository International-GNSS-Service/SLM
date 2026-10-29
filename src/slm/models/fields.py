# upstream/fields.py
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

validate_station_name_characters = RegexValidator(
    regex=r"\A[^/\\.\s\x00-\x1f]+\Z",
    message=_(
        "Station names may not contain path separators, dots, whitespace or "
        "control characters."
    ),
    code="unsafe_station_name",
)
"""
Station names are used as filesystem path components and URL segments, so this
baseline rule always applies, independent of any :setting:`SLM_STATION_NAME_REGEX`
a deployment configures on top of it.
"""


class StationNameField(models.CharField):
    """
    The StationNameField allows validation and help text to be configured in settings.
    These values will not be deconstructed into the migration files allowing users of
    the SLM to define their own semantics and validation logic around station names.

    Regardless of configuration, names are always required to be safe for use as a
    path component and URL segment (see :data:`validate_station_name_characters`).
    """

    # default_validators are never serialized into migrations, so this baseline
    # rule can be enforced unconditionally without touching deconstruct().
    default_validators = [validate_station_name_characters]

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
