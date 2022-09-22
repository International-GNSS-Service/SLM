from django import template
from slm.utils import to_snake_case
from django.utils.translation import gettext as _
from datetime import datetime

register = template.Library()


@register.filter(name='section_name')
def section_name(form):
    return form.section_name()


@register.filter(name='to_snake')
def to_snake(string):
    return to_snake_case(string)


@register.filter(name='arg')
def arg(arg1,arg2):
    if isinstance(arg1, list):
        return arg1 + [arg2]
    return [arg1, arg2]


@register.filter(name='to_id')
def to_id(arg1, arg2):
    if not isinstance(arg1, list):
        arg1 = [arg1]
    return '-'.join([to_snake_case(str(arg)) for arg in arg1 + [arg2] if arg])


@register.filter(name='key_value')
def key_value(dictionary, key):
    return dictionary.get(key, None)


@register.filter(name='is_moderator')
def is_moderator(user, station):
    return user.is_moderator(station)


@register.filter(name='value_filter')
def value_filter(value):
    if value is None:
        return _('empty')
    str_val = str(value)
    if str_val is None or value == '':
        return _('empty')
    return str_val


@register.filter(name='strip_ms')
def strip_ms(timestamp):
    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()
    return ':'.join(timestamp.split(':')[0:2])


@register.filter(name='help_text')
def help_text(model, field):
    return model._meta.get_field(field).help_text
