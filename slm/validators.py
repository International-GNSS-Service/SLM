from collections import namedtuple
from datetime import datetime

from slm.defines import FlagSeverity
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


# we can't use actual nulls for times because it breaks things like
# Greatest on MYSQL
NULL_TIME = datetime.utcfromtimestamp(0)


Flag = namedtuple('Flag', 'message manual severity')


def get_validators(model, field):
    from django.conf import settings
    """
    Get the validator list for a given model and field from validation 
    settings.
    
    :param model: The Django model name <app_name>.<ModelClass>
    :param field: The field name 
    :return:
    """
    return getattr(
        settings, 'SLM_DATA_VALIDATORS', {}
    ).get(model, {}).get(field, [])


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
        return getattr(settings, 'SLM_VALIDATION_BYPASS_BLOCK')
    return bool(BYPASS_BLOCKS)


class SLMValidator:

    severity = FlagSeverity.NOTIFY

    def __init__(self, *args, **kwargs):
        self.severity = kwargs.pop('severity', self.severity)
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


class FieldPreferred(SLMValidator):

    statement = 'This field is recommended'

    def __call__(self, instance, field, value):
        if isinstance(value, str):
            value = value.strip()
        if not value or value == NULL_TIME:
            self.throw_error(f'{_(self.statement)}.', instance, field)


class FieldRequiredToPublish(FieldPreferred):

    statement = 'This field is required to publish'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, severity=FlagSeverity.BLOCK_PUBLISH, **kwargs)


class EnumValidator(FieldPreferred):

    statement = _('Value not in Enumeration.')

    def __call__(self, instance, field, value):
        if isinstance(value, str):
            value = value.strip()
        if value not in {None, ''}:
            try:
                field.enum(value)
            except ValueError:
                self.throw_error(self.statement, instance, field)


class FourIDValidator(SLMValidator):

    regex_val = RegexValidator(regex=r'[A-Z0-9]{4}')

    def __call__(self, instance, field, value):
        self.validate(
            instance,
            field,
            lambda: self.regex_val(value)
        )
        if not instance.site.name.startswith(value):
            self.throw_error(
                f'{field.verbose_name} '
                f'{_("must be the prefix of the 9 character site name")}.',
                instance,
                field
            )


class ARPValidator(SLMValidator):

    def __call__(self, instance, field, value):
        at_arp = getattr(
            getattr(instance, 'antenna_type', None),
            'reference_point',
            None
        )
        if at_arp != value:
            self.throw_error(
                f'{getattr(value, "name", None)} '
                f'{_("must does not match the antenna reference point: ")}'
                f'{getattr(at_arp, "name", None)}.',
                instance,
                field
            )


class TimeRangeValidator(SLMValidator):

    start_field = None
    end_field = None

    def __init__(self, *args, severity=FlagSeverity.BLOCK_SAVE, **kwargs):
        self.start_field = kwargs.pop('start_field', None)
        self.end_field = kwargs.pop('end_field', None)
        assert(not (self.start_field and self.end_field))
        super().__init__(*args, severity=severity, **kwargs)

    def __call__(self, instance, field, value):
        if self.start_field:
            start = getattr(instance, self.start_field, None)
            if start is not None and start != NULL_TIME and value:
                if start > value:
                    self.throw_error(
                        f'{field.verbose_name} '
                        f'{_("must be greater than")} '
                        f'{instance._meta.get_field(self.start_field).verbose_name}',
                        instance,
                        field
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
                        f'{_("Cannot define")} '
                        f'{instance._meta.get_field(self.end_field).verbose_name} '
                        f'{_("without defining")} '
                        f'{field.verbose_name}.',
                        instance,
                        field
                    )
                elif end < value:
                    self.throw_error(
                        f'{field.verbose_name} '
                        f'{_("must be less than")} '
                        f'{instance._meta.get_field(self.end_field).verbose_name}',
                        instance,
                        field
                    )
