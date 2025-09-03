import json
import os
from datetime import datetime, timezone
from enum import Enum
from html import unescape
from typing import Iterable

from chardet import detect
from django import template
from django.conf import settings
from django.urls import resolve
from django.utils.translation import gettext as _

from slm.utils import build_absolute_url, decimal_to_dddmmssss, to_snake_case

register = template.Library()


@register.filter(name="pad_diff")
def pad_diff(int1, int2):
    return " " * (int(int1) - int(int2))


@register.filter(name="div")
def div(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


@register.filter(name="section_name")
def section_name(form):
    return form.section_name()


@register.filter(name="to_snake")
def to_snake(string):
    return to_snake_case(string)


@register.filter(name="arg")
def arg(arg1, arg2):
    if isinstance(arg1, list):
        return arg1 + [arg2]
    return [arg1, arg2]


@register.filter(name="to_id")
def to_id(arg1, arg2):
    if not isinstance(arg1, list):
        arg1 = [arg1]
    return "-".join([to_snake_case(str(arg)) for arg in arg1 + [arg2] if arg])


@register.filter(name="key_value")
def key_value(dictionary, key):
    return dictionary.get(key, None)


@register.filter(name="value_filter")
def value_filter(value):
    if value is None:
        return _("empty")
    str_val = str(value)
    if str_val is None or value == "":
        return _("empty")
    return str_val


@register.filter(name="strip_ms")
def strip_ms(timestamp):
    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()
    return ":".join(timestamp.split(":")[0:2])


@register.filter(name="help_text")
def help_text(model, field):
    return model._meta.get_field(field).help_text


@register.filter(name="simple_utc")
def simple_utc(datetime_field):
    """
    Return a datetime string in UTC, in the format YYYY-MM-DD HH:MM

    :param datetime_field: A datetime object
    :return: formatted datetime string
    """
    if datetime_field:
        if isinstance(datetime_field, datetime):
            return datetime_field.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        return datetime_field.strftime("%Y-%m-%d")
    return ""


@register.filter(name="iso_utc")
def iso_utc(datetime_field):
    if datetime_field:
        return datetime_field.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    return ""


@register.filter(name="iso_utc_full")
def iso_utc_full(datetime_field):
    if datetime_field:
        return datetime_field.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ""


@register.filter(name="multi_line")
def multi_line(text):
    if text:
        limit = 48
        lines = [line.rstrip() for line in text.split("\n")]
        limited = []
        for line in lines:
            while len(line) > limit:
                mark = limit

                # only chop on white space if we can
                for ridx, char in enumerate(reversed(line[0:limit])):
                    if not char.strip():
                        mark = limit - ridx
                        break

                limited.append(unescape(line[0:mark]))
                line = line[mark:]
            limited.append(unescape(line))
        return f"\n{' ' * 30}: ".join([line for line in limited if line.strip()])
    return ""


@register.filter(name="iso6709")
def iso6709(decimal_degrees, padding):
    if decimal_degrees:
        dddmmssss = decimal_to_dddmmssss(decimal_degrees)
        number = f"{dddmmssss:.2f}"
        integer, dec = number.split(".") if "." in number else (number, None)
        iso_frmt = f"{abs(int(integer)):0{int(padding)}}{'.' if dec else ''}{dec}"
        return f"{'+' if float(dddmmssss) > 0 else '-'}{iso_frmt}"
    return ""


@register.filter(name="epsg7912")
def epsg7912(lat_lng, prec=10):
    return precision(lat_lng, prec)


@register.filter(name="precision")
def precision(number, prec):
    if number or number == 0:
        return f"{number:.{prec}f}".rstrip("0").rstrip(".")
    return ""


@register.filter(name="precision_full")
def precision_full(alt, prec):
    if alt or alt == 0:
        return f"{alt:.{prec}f}"
    return ""


@register.filter(name="pos")
def pos(number):
    if number or number == 0:
        if float(number) > 0:
            return f"+{number}"
        return number
    return ""


@register.filter(name="none2empty")
def none2empty(number, suffix=""):
    if number or number == 0:
        return f"{number}{suffix}"
    return ""


@register.filter(name="enum_str")
def enum_str(value):
    if value is None:
        return ""
    if isinstance(value, Enum):
        return value.label
    return value


@register.filter(name="satellite_str")
def satellite_str(satellite_systems):
    if satellite_systems:
        return "+".join([system.name for system in satellite_systems.all()])
    return ""


@register.filter(name="inspect")
def inspect(obj):
    from pprint import pprint

    pprint(f"{obj}:")
    pprint(dir(obj))


@register.filter(name="get_key")
def get_key(obj, key):
    return obj.get(key)


@register.filter(name="has_key")
def has_key(obj, key):
    try:
        return key in obj
    except TypeError:
        return hasattr(obj, key)


@register.filter(name="merge")
def merge(obj1, obj2):
    return obj1.merge(obj2)


@register.filter(name="antenna_radome")
def antenna_radome(antenna):
    spacing = max(abs(16 - len(antenna.antenna_type.model)), 1)
    radome = "NONE"
    if hasattr(antenna, "radome_type"):
        radome = antenna.radome_type.model
    return f"{antenna.antenna_type.model}{' ' * spacing}{radome}"


@register.filter(name="antenna_codelist")
def antenna_codelist(antenna):
    radome = "NONE"
    if hasattr(antenna, "radome_type"):
        radome = antenna.radome_type.model
    return f"{antenna.antenna_type.model} {radome}"


@register.filter(name="rpad_space")
def rpad_space(text, length):
    return f"{text}{' ' * (int(length) - len(str(text)))}"


@register.filter(name="file_icon")
def file_icon(file):
    subtype = ""
    if file:
        subtype = getattr(
            file, "mimetype", file if isinstance(file, str) else ""
        ).split("/")[-1]
    return getattr(settings, "SLM_FILE_ICONS", {}).get(subtype, "bi bi-file-earmark")


@register.filter(name="file_lines")
def file_lines(file):
    if isinstance(file, str):
        return file.splitlines()
    if file and os.path.exists(file.file.path):
        content = file.file.open().read()
        try:
            return content.decode(detect(content).get("encoding", "utf-8")).splitlines()
        except (UnicodeDecodeError, LookupError, ValueError):
            return [
                _("** Unable to determine text encoding - please upload as UTF-8. **")
            ]
    return [""]


@register.filter(name="finding_class")
def finding_class(findings, line_number):
    # in json keys can't be integers and our findings context might be integers
    # or strings if its gone through a json cycle so we try both
    if findings:
        return {
            "E": "slm-parse-error",
            "W": "slm-parse-warning",
            "I": "slm-parse-ignore",
        }.get(findings.get(str(line_number), findings.get(int(line_number), [""]))[0])
    return ""


@register.filter(name="finding_content")
def finding_content(findings, line_number):
    if findings:
        return findings.get(
            str(line_number), findings.get(int(line_number), [None, ""])
        )[1]
    return ""


@register.filter(name="finding_title")
def finding_title(findings, line_number):
    if findings:
        return {"E": "Error", "W": "Warning", "I": "Ignored"}.get(
            findings.get(str(line_number), findings.get(int(line_number), [""]))[0]
        )
    return ""


# these filters support marking slices of lines with a finding given a column range
# its messy - could use a refactor and also currently doesnt support more than one marking per line
# if you do refactor be sure to support old findings contexts that are cached in the DB for previous
# uploads!
@register.filter(name="get_part")
def get_part(slice, line):
    return line[slice[0] : slice[1]]


@register.filter(name="clear_prefix")
def clear_prefix(findings, line_number):
    if findings:
        ret = findings.get(
            str(line_number), findings.get(int(line_number), [None, "", None])
        )
        if len(ret) >= 3 and ret[2]:
            return None, ret[2][0]
    return 0, 0


@register.filter(name="marked_part")
def marked_part(findings, line_number):
    if findings:
        ret = findings.get(
            str(line_number), findings.get(int(line_number), [None, "", None])
        )
        if len(ret) >= 3 and ret[2]:
            return ret[2][0], ret[2][1]
    return None, None


@register.filter(name="clear_postfix")
def clear_postfix(findings, line_number):
    if findings:
        ret = findings.get(str(line_number), findings.get(int(line_number), [None, ""]))
        if len(ret) >= 3 and ret[2]:
            return ret[2][1], None
    return 0, 0


@register.filter(name="split_rows")
def split_rows(iterable, row_length):
    rows = []
    row = []
    for idx, item in enumerate(iterable):
        row.append(item)
        if idx + 1 % row_length == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


@register.filter(name="rstrip")
def rstrip(to_strip, characters):
    if to_strip:
        return to_strip.rstrip(characters)
    return to_strip


@register.filter(name="lstrip")
def lstrip(to_strip, characters):
    if to_strip:
        return to_strip.lstrip(characters)
    return to_strip


@register.filter(name="absolute_url")
def absolute_url(path, request=None):
    return build_absolute_url(path, request=request)


@register.filter(name="file_url")
def file_url(path, request=None):
    file_domain = getattr(settings, "SLM_FILE_DOMAIN", None)
    if file_domain:
        return f"{file_domain.rstrip('/')}/{path.lstrip('/')}"
    return absolute_url(path, request=request)


@register.filter(name="contact")
def contact(agency, ctype):
    return {
        field: getattr(agency, f"{ctype}_{field}")
        for field in ["name", "phone1", "phone2", "fax", "email"]
        if getattr(agency, f"{ctype}_{field}", None)
    }


@register.filter(name="format_temp_stab")
def format_temp_stab(temp, temp_stab):
    temp = precision(temp, 1)
    temp_stab = precision(temp_stab, 1)
    if temp and temp_stab:
        return f"{temp} +/- {temp_stab} C"
    elif temp:
        return f"{temp} C"
    elif temp_stab:
        return f"+/- {temp_stab} C"
    return ""


@register.filter(name="class_name")
def class_name(cls):
    if isinstance(cls, type):
        return cls.__name__
    return cls.__class__.__name__


@register.filter(name="model_meta")
def model_meta(cls, parameter):
    return getattr(cls._meta, parameter)


@register.filter(name="params")
def params(iterable, parameter):
    return (getattr(obj, parameter) for obj in iterable)


@register.filter(name="section_field_classes")
def section_field_classes(field, form):
    classes = [
        {"checkbox": ""}.get(  #'form-check-input'
            getattr(field.field.widget, "input_type", None), "form-control"
        )
    ]
    if form.flags.get(field.name, None):
        classes.append("is-invalid")
    elif form.diff.get(field.name, None):
        classes.append("is-invalid")
        classes.append("slm-form-unpublished")
    return " ".join(classes)


@register.filter(name="alert_class")
def alert_class(message):
    """Get the css class for a Django message"""
    return {"error": "danger", "debug": "secondary", "info": "primary"}.get(
        message.level_tag, message.level_tag
    )


@register.filter(name="autocomplete_values")
def autocomplete_values(widget):
    """
    Return a list of json strings representing the default values of
    autocomplete fields -see forms. We have to do some snooping around the api
    and call the serializer directly.
    """
    values = widget.get("value", None)
    if "optgroups" in widget:
        values = []
        for _, choices, _ in widget.get("optgroups"):
            values.extend([str(choice["value"]) for choice in choices])

    items = []
    if values:
        if isinstance(values, str) or not isinstance(values, Iterable):
            values = [values]

        service_url = widget.get("attrs", {}).get("data-service-url")

        value_map = {
            item["value"]: item
            for item in json.loads(
                str(widget.get("attrs", {}).get("data-source", "[]"))
            )
        }
        if value_map:
            for value in values:
                if value in value_map:
                    items.append(json.dumps(value_map[value]))

        elif service_url:
            view, _, _ = resolve(service_url)
            Serializer = view.cls.serializer_class
            field = widget.get("attrs", {}).get("data-value-param", "pk")
            serializer = Serializer(
                Serializer.Meta.model.objects.filter(**{f"{field}__in": values}),
                many=True,
            )
            for value in serializer.data:
                items.append(json.dumps(value))

    return items


@register.simple_tag(takes_context=True)
def set_global(context, name, val):
    context.render_context[name] = val
    return ""


@register.simple_tag(takes_context=True)
def get_global(context, name):
    return context.render_context.get(name, None)


@register.filter(name="chop_time")
def chop_time(filename):
    """
    Chop the time ext off of a sitelog filename.

    e.g. SITE_YYYYMMDD_HHMMSS.log -> SITE_YYYYMMDD_HHMMSS.log
    """
    if filename.count("_") == 2:
        return f"{filename[: filename.rindex('_')]}{filename[filename.rindex('.') :]}"
    return filename


@register.filter(name="chop_datetime")
def chop_datetime(filename):
    """
    Chop the date and time ext off of a sitelog filename.

    e.g. SITE_YYYYMMDD_HHMMSS.log -> SITE.log
    """
    if "_" in filename:
        return f"{filename[: filename.index('_')]}{filename[filename.rindex('.') :]}"
    return filename
