from collections import namedtuple
from datetime import datetime, timezone

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Model
from django.utils.translation import gettext_lazy as _

from slm.defines import EquipmentState, FlagSeverity

# we can't use actual nulls for times because it breaks things like
# Greatest on MYSQL
# NULL_TIME = datetime.utcfromtimestamp(0)
NULL_TIME = datetime.fromtimestamp(0, timezone.utc)
NULL_VALUES = [None, "", NULL_TIME]


Flag = namedtuple("Flag", "message manual severity")


def get_validators(model, field):
    """
    Get the validator list for a given model and field from validation
    settings.

    :param model: The Django model name <app_name>.<ModelClass>
    :param field: The field name
    :return:
    """
    from django.conf import settings

    if isinstance(model, Model) or (
        isinstance(model, type) and issubclass(model, Model)
    ):
        model = model._meta.label
    return getattr(settings, "SLM_DATA_VALIDATORS", {}).get(model, {}).get(field, [])


# toggle this flag to allow save block bypassing.
BYPASS_BLOCKS = None


def set_bypass(toggle):
    global BYPASS_BLOCKS
    BYPASS_BLOCKS = bool(toggle)


def bypass_block():
    """
    Return if we should bypass any validation save blocking. This setting
    is controlled by the SLM_VALIDATION_BYPASS_BLOCK setting in settings or
    can be preempted by toggling the BYPASS_BLOCKS flag above.

    This is important when working with legacy data. All validators should
    respect this flag.

    :return: True if we should bypass any save blocks
    """
    from django.conf import settings

    if BYPASS_BLOCKS is None:
        return getattr(settings, "SLM_VALIDATION_BYPASS_BLOCK")
    return bool(BYPASS_BLOCKS)


class SLMValidator:
    severity = FlagSeverity.NOTIFY

    def __init__(self, *args, **kwargs):
        self.severity = kwargs.pop("severity", self.severity)
        super().__init__(*args, **kwargs)

    def __call__(self, instance, field, value):
        raise NotImplementedError()

    def validate(self, instance, field, validator):
        try:
            validator()
        except ValidationError as ve:
            if self.severity == FlagSeverity.BLOCK_SAVE and not bypass_block():
                raise ve
            self.throw_flag(ve.message, instance, field)

    def throw_error(self, message, instance, field):
        if self.severity == FlagSeverity.BLOCK_SAVE and not bypass_block():
            raise ValidationError(_(message))
        self.throw_flag(message, instance, field)

    def throw_flag(self, message, instance, field):
        if not instance._flags:
            instance._flags = {}
        instance._flags[field.name] = message
        instance.save()


class FieldRequired(SLMValidator):
    required_msg = _("This field is required.")
    desired_msg = _("This field is desired.")

    allow_legacy_nulls = False

    desired = False

    def __init__(self, allow_legacy_nulls=allow_legacy_nulls, desired=desired):
        self.allow_legacy_nulls = allow_legacy_nulls
        self.desired = desired
        super().__init__(severity=FlagSeverity.BLOCK_SAVE)

    def __call__(self, instance, field, value):
        if isinstance(value, str):
            value = value.strip()
        if value in NULL_VALUES:
            if (
                self.desired
                or not self.allow_legacy_nulls
                or instance.get_initial_value(field.name) in NULL_VALUES
            ):
                self.throw_flag(self.desired_msg, instance, field)
            else:
                self.throw_error(self.required_msg, instance, field)


class EnumValidator(SLMValidator):
    statement = _("Value not in Enumeration.")

    def __call__(self, instance, field, value):
        if isinstance(value, str):
            value = value.strip()
        if value not in NULL_VALUES:
            try:
                field.enum(value)
            except ValueError:
                self.throw_error(self.statement, instance, field)


class VerifiedEquipmentValidator(SLMValidator):
    statement = _("This equipment code has not been verified.")

    def __call__(self, instance, field, value):
        if value.state == EquipmentState.UNVERIFIED:
            self.throw_error(self.statement, instance, field)
        elif value.state == EquipmentState.LEGACY:
            self.throw_error(self.statement, instance, field)


class ActiveEquipmentValidator(SLMValidator):
    statement = _("This equipment code is no longer in use.")
    replaced_statement = _("This equipment code has been replaced by: {}.")

    def __call__(self, instance, field, value):
        if value.state == EquipmentState.LEGACY:
            if value.replaced_by.exists():
                self.throw_error(
                    self.replaced_statement.format(
                        ", ".join([eq.model for eq in value.replaced_by.all()])
                    ),
                    instance,
                    field,
                )
            else:
                self.throw_error(self.statement, instance, field)


class NonEmptyValidator(SLMValidator):
    statement = _("More than zero selections should be made.")

    def __call__(self, instance, field, value):
        if not value.all():
            self.throw_error(self.statement, instance, field)


class FourIDValidator(SLMValidator):
    regex_val = RegexValidator(regex=r"[A-Z0-9]{4}")

    def __call__(self, instance, field, value):
        self.validate(instance, field, lambda: self.regex_val(value))
        if not instance.site.name.startswith(value):
            self.throw_error(
                f"{field.verbose_name} "
                f"{_('must be the prefix of the 9 character site name')}.",
                instance,
                field,
            )


class ARPValidator(SLMValidator):
    def __call__(self, instance, field, value):
        at_arp = getattr(
            getattr(instance, "antenna_type", None), "reference_point", None
        )
        if at_arp != value:
            self.throw_error(
                f"{getattr(value, 'name', None)} "
                f"{_('must does not match the antenna reference point: ')}"
                f"{getattr(at_arp, 'name', None)}.",
                instance,
                field,
            )


class TimeRangeBookendValidator(SLMValidator):
    """
    Ensures that sections that should not have overlapping time ranges
    are properly bookended - i.e. that the time range fields are closed before
    the next section starts.
    """

    accessor: str
    bookend_field: str

    def __init__(
        self, *args, bookend_field="installed", severity=FlagSeverity.NOTIFY, **kwargs
    ):
        self.bookend_field = bookend_field
        assert self.bookend_field, "Bookend field must be specified."
        super().__init__(*args, severity=severity, **kwargs)

    def __call__(self, instance, field, value):
        sections = (
            getattr(
                instance.site,
                instance._meta.get_field("site").remote_field.get_accessor_name(),
            )
            .head()
            .sort(reverse=True)
        )
        last = sections[0]
        for section in sections[1:]:
            # todo - this should be unnecessary when validation system is made
            #   more robust
            if "Must end before" in section._flags.get(field.name, ""):
                del section._flags[field.name]
                section.save()
            ######

            last_start = getattr(last, self.bookend_field, None)
            if getattr(section, field.name, None) is None or (
                last_start and last_start < getattr(section, field.name)
            ):
                self.throw_error(
                    _("Must end before {} starts {}.").format(
                        last, getattr(last, self.bookend_field, None)
                    ),
                    section,
                    field,
                )

            last = section


class TimeRangeValidator(SLMValidator):
    start_field = None
    end_field = None

    def __init__(self, *args, severity=FlagSeverity.BLOCK_SAVE, **kwargs):
        self.start_field = kwargs.pop("start_field", None)
        self.end_field = kwargs.pop("end_field", None)
        assert not (self.start_field and self.end_field)
        super().__init__(*args, severity=severity, **kwargs)

    def __call__(self, instance, field, value):
        if self.start_field:
            start = getattr(instance, self.start_field, None)
            if start is not None and start != NULL_TIME and value:
                if start > value:
                    self.throw_error(
                        f"{field.verbose_name} "
                        f"{_('must be greater than')} "
                        f"{instance._meta.get_field(self.start_field).verbose_name}",
                        instance,
                        field,
                    )
        if self.end_field:
            end = getattr(instance, self.end_field, None)
            if end is not None and end != NULL_TIME:
                if (
                    value is None
                    or value == NULL_TIME
                    and end is not None
                    and end != NULL_TIME
                ):
                    self.throw_error(
                        f"{_('Cannot define')} "
                        f"{instance._meta.get_field(self.end_field).verbose_name} "
                        f"{_('without defining')} "
                        f"{field.verbose_name}.",
                        instance,
                        field,
                    )
                elif end < value:
                    self.throw_error(
                        f"{field.verbose_name} "
                        f"{_('must be less than')} "
                        f"{instance._meta.get_field(self.end_field).verbose_name}",
                        instance,
                        field,
                    )


class PositionsMatchValidator(SLMValidator):
    """
    Attach this validator to SiteLocation llh and/or xyz fields to validate that these
    positions are within the given tolerance of each other.
    """

    tolerance = 1.0
    """
    3D tolerance in meters between the positions before flagging.
    """

    def __init__(
        self,
        *args,
        severity=FlagSeverity.BLOCK_SAVE,
        tolerance: float = tolerance,
        **kwargs,
    ):
        self.tolerance = tolerance
        super().__init__(*args, severity=severity, **kwargs)

    def __call__(self, instance, field, value):
        from math import sqrt

        from slm.utils import llh2xyz

        fieldname = field.name
        xyz1 = value if fieldname == "xyz" else llh2xyz(value)
        other = "xyz" if fieldname == "llh" else "llh"
        otherfield = instance._meta.get_field(other)
        if xyz1:
            xyz2 = (
                llh2xyz(getattr(instance, other))
                if other == "llh"
                else getattr(instance, other)
            )
            if xyz2:
                diff = sqrt(
                    (xyz1[0] - xyz2[0]) ** 2
                    + (xyz1[1] - xyz2[1]) ** 2
                    + (xyz1[2] - xyz2[2]) ** 2
                )
                if diff > self.tolerance:
                    self.throw_error(
                        f"{diff:.2f} meters away from {otherfield.verbose_name}",
                        instance,
                        field,
                    )
