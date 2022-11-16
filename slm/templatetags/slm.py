from django import template
from slm.utils import to_snake_case
from django.utils.translation import gettext as _
from datetime import datetime, timezone, date

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


@register.filter(name='simple_utc')
def simple_utc(datetime_field):
    """
    Return a datetime string in UTC, in the format YYYY-MM-DD HH:MM

    :param datetime_field: A datetime object
    :return: formatted datetime string
    """
    if datetime_field:
        if isinstance(datetime_field, date):
            return datetime_field.strftime('%Y-%m-%d')
        return datetime_field.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M')
    return ''

@register.filter(name='iso_utc')
def iso_utc(datetime_field):
    if datetime_field:
        return datetime_field.astimezone(
            timezone.utc
        ).strftime('%Y-%m-%dT%H:%MZ')
    return ''


@register.filter(name='multi_line')
def multi_line(text):
    if text:
        limit = 49
        lines = text.split('\n')
        limited = []
        for line in lines:
            while len(line) > limit:
                limited.append({line[0:limit]})
                line = line[limit:]
            limited.append(line)
        return f'\n{" "*30}: '.join(limited)
    return ''


@register.filter(name='iso6709')
def iso6709(lat_lng):
    if lat_lng:
        return f'{"+" if lat_lng > 0 else ""}{lat_lng:.2f}'
    return ''


@register.filter(name='precision')
def precision(alt, precision):
    if alt:
        return f'{alt:.{precision}f}'.rstrip('0').rstrip('.')
    return ''


@register.filter(name='pos')
def pos(number):
    if float(number) > 0:
        return f'+{number}'
    return number
