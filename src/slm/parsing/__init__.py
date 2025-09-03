import re
import typing as t
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Union

from dateutil.parser import parse as parse_date
from dateutil.tz.tz import tzlocal
from django.contrib.gis.geos import Point

from slm.models.equipment import Antenna, Radome, Receiver, SatelliteSystem
from slm.utils import dddmmssss_to_decimal

SPECIAL_CHARACTERS = "().,-_[]{}<>+%"
NUMERIC_CHARACTERS = ".+-Ee"
SKIPPED_NUMERICS = "',()"
NULL_VALUES = [
    "unknown",
    "unkn",
    "n/a",
    "none",
    "not measured",
    "provisional",
    "?",
    "programmable",
]

ACCURACY_PREFIXES = [
    "approx.",
    "approx",
    "+-",
    "-+",
    "+/-",
    "-/+",
    "±",
    "~",
    "<",
    "Better than",
    "=/-",
    "+/_",  # common QWERTY typos
]
METERS = ["m", "m.", "meter", "meters"]

TZ_INFOS = {"UT": timezone.utc, "UTUT": timezone.utc}


def remove_from_start(value: str, prefixes: List[str]):
    pattern = re.compile(
        r"^("
        + "|".join(
            [re.escape(prefix.strip()).replace(r"\ ", r"\s*") for prefix in prefixes]
        )
        + r")\s*",
        re.IGNORECASE,
    )
    result = pattern.sub("", value).strip()
    return result


@dataclass
class _Ignored:
    msg: str = ""
    columns: t.Optional[t.Tuple[int, int]] = None


@dataclass
class _Warning:
    """Used to wrap a warning message with a value as the return type for binding functions"""

    msg: str
    value: Any


def normalize(name):
    """
    Normalization is designed to remove any superficial variable name
    mismatches. We remove all special characters and spaces and then
    upper case the name.
    """
    for char in SPECIAL_CHARACTERS + " \t":
        name = name.replace(char, "")
    return name.upper().strip()


class Finding:
    """
    A base class for parser/binding findings.
    """

    lineno: int
    parser: "BaseParser"
    message: str
    section: t.Optional["BaseSection"]
    parameter: t.Optional["BaseParameter"]
    line: t.Optional[str]
    priority: int = 0
    columns: t.Optional[t.Tuple[int, int]]

    def __init__(
        self,
        lineno,
        parser,
        message,
        section=None,
        parameter=None,
        line=None,
        columns=None,
    ):
        self.lineno = lineno
        self.parser = parser
        self.message = message
        self.section = section
        self.parameter = parameter
        self.line = line
        self.columns = columns

    def __str__(self):
        return (
            f"({self.lineno + 1: 4}) {self.parser.lines[self.lineno]}"
            f"{' ' * (80 - len(self.parser.lines[self.lineno]))}"
            f"[{self.level.upper()}]: {self.message}"
        )

    @property
    def level(self) -> str:
        return self.__class__.__name__.lower()


class Ignored(Finding):
    level = "I"


class Error(Finding):
    priority = 5

    level = "E"


class Warn(Finding):
    priority = 4

    level = "W"


class BaseParameter:
    name = ""
    parser = None
    section = None
    line_no = None
    line_end = None
    values = None

    binding = None

    @property
    def is_placeholder(self):
        return False

    @property
    def is_empty(self):
        return not self.value.strip()

    @property
    def num_lines(self):
        return self.line_end - self.line_no + 1

    @property
    def lines(self):
        return self.parser.lines[self.line_no : self.line_end]

    def __init__(self, line_no, name, values, parser, section):
        self.line_no = line_no
        self.line_end = line_no
        self.parser = parser
        self.section = section
        self.name = name
        self.values = values

    def append(self, line_no, match):
        self.line_end = line_no
        self.values.append(match.group(1).strip())

    @property
    def value(self):
        return "\n".join(self.values)

    @property
    def normalized_name(self):
        return normalize(self.name)

    def bind(self, name, value):
        if self.binding is None:
            self.binding = {}
        self.binding[name] = value
        self.section.bind(name, self, value)

    def __str__(self):
        if self.is_placeholder:
            return f"{self.name} [PLACEHOLDER]: {self.value}"
        return f"{self.name}: {self.value}"


class BaseSection:
    line_no = None
    line_end = None
    section_number = None
    subsection_number = None
    order = None
    header = ""

    parameters: Dict[str, BaseParameter]
    example = False

    _param_binding_: Dict[str, List[BaseParameter]] = None
    _binding_: Dict[str, Union[str, int, float, date, datetime]] = None

    def get_params(self, name: str) -> List[BaseParameter]:
        """
        Get parameter by parsing or bound name.
        """
        self._param_binding_ = self._param_binding_ or {}
        return self._param_binding_.get(
            name,
            (
                [self.parameters[normalize(name)]]
                if normalize(name) in self.parameters
                else []
            ),
        )

    def bind(self, name, parameter, value):
        """
        Bind a parameter to the given name and value.
        """
        self._binding_ = self._binding_ or {}
        self._param_binding_ = self._param_binding_ or {}
        self._param_binding_.setdefault(name, []).append(parameter)
        self._binding_[name] = value

    def collate(self, params, param, value):
        """
        Combine the given bound params into a new single binding.
        """
        self._binding_ = self._binding_ or {}
        self._param_binding_ = self._param_binding_ or {}
        self._binding_[param] = value
        for collated in params:
            parsed_params = self._param_binding_.get(collated, [])
            self._param_binding_.setdefault(param, []).extend(parsed_params)
            if parsed_params:
                del self._param_binding_[collated]

    @property
    def binding(self) -> Optional[Dict[str, Union[str, int, float, date, datetime]]]:
        return self._binding_

    @property
    def ordering_id(self):
        if self.order:
            return self.order
        if self.subsection_number:
            return self.subsection_number
        return None

    def __init__(self, line_no, section_number, subsection_number, order, parser):
        self.parameters = {}
        self.line_no = line_no
        self.line_end = line_no
        self.section_number = section_number
        self.subsection_number = subsection_number
        self.order = order
        self.parser = parser

        if isinstance(self.subsection_number, str) and self.subsection_number.isdigit():
            self.subsection_number = int(self.subsection_number)

        if isinstance(self.order, str) and self.order.isdigit():
            self.order = int(self.order)

    def __str__(self):
        section_str = f"{self.index_string} {self.header}\n"
        if self.example:
            section_str = f"{self.index_string} {self.header} (EXAMPLE)\n"
        for param in self.parameters.values():
            section_str += f"\t{param}\n"
        return section_str

    @property
    def contains_values(self):
        """
        True if any parameter in this section contains a real value that is
        not a placeholder.
        """
        for param in self.parameters.values():
            if not (param.is_empty or param.is_placeholder):
                return True
        return False

    @property
    def index_string(self):
        index = f"{self.section_number}"
        if self.subsection_number or self.example:
            index += "."
            if self.subsection_number:
                index += str(self.subsection_number)
            else:
                index += "x"
            if self.subsection_number and (self.order or self.example):
                index += f".{self.order if self.order else 'x'}"
        return index

    @property
    def index_tuple(self):
        return self.section_number, self.subsection_number, self.order

    @property
    def heading_index(self):
        if self.order is not None:
            return self.section_number, self.subsection_number
        return self.section_number

    def add_parameter(self, parameter):
        if parameter.normalized_name in self.parameters:
            self.parser.add_finding(
                Error(
                    parameter.line_no,
                    self.parser,
                    f"Duplicate parameter: {parameter.name}",
                    section=self,
                )
            )
        else:
            self.parameters[parameter.normalized_name] = parameter
            if self.line_end < parameter.line_end:
                self.line_end = parameter.line_end
        return parameter


class BaseParser:
    """
    A base parser that tracks findings at specific lines.
    """

    lines: Optional[List[str]]

    name_matched: bool = None
    site_name: str = None

    _findings_: Dict[int, Finding]

    """
    Sections indexed by section number tuple 
    (section_number, subsection_number, order)
    """
    sections: Dict[Tuple[int, Optional[int], Optional[int]], BaseSection]

    @property
    def findings(self) -> Dict[int, Finding]:
        """
        Return findings dictionary keyed by line number and ordered by
        line number.
        """
        # dictionaries are ordered in python 3.7+
        return dict(sorted(self._findings_.items()))

    @property
    def findings_context(self) -> Dict[int, Tuple[str, str]]:
        return {
            int(line): (finding.level, finding.message, finding.columns)
            for line, finding in self.findings.items()
        }

    @property
    def context(self):
        return {"site": self.site_name, "findings": self.findings_context}

    @property
    def ignored(self):
        return {
            lineno: finding
            for lineno, finding in self._findings_.items()
            if isinstance(finding, Ignored)
        }

    @property
    def errors(self):
        return {
            lineno: finding
            for lineno, finding in self._findings_.items()
            if isinstance(finding, Error)
        }

    @property
    def warnings(self):
        return {
            lineno: finding
            for lineno, finding in self._findings_.items()
            if isinstance(finding, Warn)
        }

    @property
    def is_valid(self):
        return len(self.errors) == 0

    @property
    def has_warnings(self):
        return len(self.warnings) == 0

    def remove_finding(self, lineno):
        if lineno in self._findings_:
            del self._findings_[lineno]

    def add_section(self, section):
        if section.index_tuple in self.sections:
            self.duplicate_section_error(section)
        self.sections[section.index_tuple] = section
        return section

    def duplicate_section_error(self, duplicate_section):
        for lineno in range(duplicate_section.line_no, duplicate_section.line_end):
            self.add_finding(
                Error(
                    lineno,
                    self,
                    f"Duplicate section {duplicate_section.index_string}",
                    section=duplicate_section,
                )
            )

    def add_finding(self, finding):
        if not isinstance(finding, Finding):
            raise ValueError(
                f"add_finding() expected a {Finding.__class__.__name__} "
                f"object, was given: {finding.__class__.__name__}."
            )
        self._findings_[finding.lineno] = finding

    def __init__(self, site_log: Union[str, List[str]], site_name: str = None) -> None:
        """
        :param site_log: The entire site log contents as a string or as a list
            of lines
        :param site_name: The expected 9-character site name of this site or
            None (default) if name is unknown
        """
        self.sections = {}
        self.site_name = site_name.upper() if site_name else site_name
        if isinstance(site_log, str):
            self.lines = site_log.split("\n")
        elif isinstance(site_log, list):
            self.lines = site_log
        else:
            raise ValueError(
                f"Expected site_log input to be string or list of lines, "
                f"given: {type(site_log)}."
            )

        self._findings_ = {}


def try_prefixes(value, converter, delimiter=" "):
    """
    A wrapper for converter functions that tries successively shorter strings
    as determined by the given delimiter. Think of this as being robust to junk
    at the end of a value.
    """

    def try_parse(prefix):
        return converter(prefix)

    parts = value.split(delimiter)
    trailing = []
    while parts:
        try:
            success = try_parse(" ".join(parts))
            if trailing:
                return _Warning(
                    msg=f"Unexpected trailing characters: {' '.join(reversed(trailing))}",
                    value=success.value if isinstance(success, _Warning) else success,
                )
            return success
        except ValueError:
            trailing.append(parts.pop())


def to_antenna(value):
    antenna = value.strip()
    parts = value.split()
    if len(parts) > 1 and len(antenna) > 16:
        antenna = value.rstrip(parts[-1]).strip()
    try:
        return Antenna.objects.get(model__iexact=antenna).model
    except Antenna.DoesNotExist:
        antennas = "\n".join([ant.model for ant in Antenna.objects.public()])
        raise ValueError(
            f"Unexpected antenna model {antenna}. Must be one of \n{antennas}"
        )


def to_radome(value):
    radome = value.strip()
    try:
        return Radome.objects.get(model__iexact=radome).model
    except Radome.DoesNotExist:
        radomes = "\n".join([rad.model for rad in Radome.objects.public()])
        raise ValueError(
            f"Unexpected radome model {radome}. Must be one of \n{radomes}"
        )


def to_receiver(value):
    receiver = value.strip()
    try:
        return Receiver.objects.get(model__iexact=receiver).model
    except Receiver.DoesNotExist:
        receivers = "\n".join([rec.model for rec in Receiver.objects.public()])
        raise ValueError(
            f"Unexpected receiver model {receiver}. Must be one of \n{receivers}"
        )


def to_satellites(value):
    sats = []
    bad_sats = set()
    for sat in [sat for sat in value.split("+") if sat]:
        try:
            upper_sat = sat.upper()
            if upper_sat == "GLONASS":
                sat = "GLO"
            elif upper_sat == "BEIDOU":
                sat = "BDS"
            elif upper_sat == "GALILEO":
                sat = "GAL"
            sats.append(SatelliteSystem.objects.get(name__iexact=sat).pk)
        except SatelliteSystem.DoesNotExist:
            bad_sats.add(sat)
    if bad_sats:
        bad_sats = "  \n".join(bad_sats)
        good_sats = "  \n".join([sat.name for sat in SatelliteSystem.objects.all()])
        raise ValueError(
            f"Expected constellation list delineated by '+' (e.g. GPS+GLO). "
            f"Unexpected values encountered: \n{bad_sats}\n\nMust be one of "
            f"\n{good_sats}"
        )
    return sats


def to_enum(enum_cls, value, strict=False, blank=None, ignored=None):
    if value:
        ignored = ignored or []
        if value.lower() in [ign.lower() for ign in ignored]:
            return _Ignored(msg=f"{value} is a placeholder.")

        parts = value.split()
        idx = len(parts)
        while idx > 0:
            try:
                return enum_cls(" ".join(parts[0:idx]))
            except ValueError:
                idx -= 1

        if not strict:
            return value.strip()

        valid_list = "  \n".join(en.label for en in enum_cls)
        raise ValueError(f"Invalid value {value} must be one of:\n{valid_list}")
    return blank


def to_numeric(
    numeric_type,
    value: str,
    units: Optional[List[str]] = None,
    prefixes: Optional[List[str]] = None,
    take_first: Optional[bool] = None,
):
    """
    The strategy for converting string parameter values to numerics is to chop
    the numeric off the front of the string. If there's any more numeric
    characters in the remainder its an error if they are not in units. Prefixes
    are also tolerated at the start. Certain delimiters are tolerated but complained about.

    :param numeric_type: The python type to return
    :param value: The string to parse
    :param units: Expected unit strings that will not be warned about.
    :param prefixes: Prefixes that if present will be removed and ignored
    :param take_first: If specified and the value is a range (e.g. 2-3) return the first element if True,
        return the second element if False and raise ValueError if None
    :return the parsed number of type numeric_type - it may also return _Ignored or a _Warning
    :raises: ValueError if no numeric could be parsed
    """
    if not value:
        return None

    if prefixes:
        value = remove_from_start(value, prefixes).strip()

    unit_start = None
    if units:
        # add parenthesis around units if they arent on
        units = [
            *units,
            *[
                f"({unit})"
                for unit in units
                if not (unit[0] == "(" and unit[-1] == ")")
            ],
        ]
        for unit in units:
            if value.endswith(unit):
                unit_start = -len(unit)
                break

    digits = ""
    end = None
    skipped = set()
    for end, char in enumerate(value[0:unit_start]):
        if char == " " and (not digits or not digits.isdigit()):
            continue
        if char.isdigit() or char in NUMERIC_CHARACTERS:
            digits += char
        elif char in SKIPPED_NUMERICS:
            skipped.add(char)
            continue
        else:
            break

    if not digits or digits.lower().endswith("e"):
        if value.startswith("("):
            return _Ignored("Looks like a placeholder.")
        for null in NULL_VALUES:
            if null in value.lower():
                return _Ignored("Looks like a null value.")
        if value.lower() in units or all(
            [part in units for part in value.lower().split(" ")]
        ):
            # some systems spit out a unit or units for when no value is present
            return _Ignored("Looks like a null value.")
        raise ValueError(f"Could not convert {value} to type {numeric_type.__name__}.")

    # there should not be any trailing text in the string unless they are expected units
    skipped = f"Unexpected delimiters: ({' '.join(list(skipped))})" if skipped else None
    if len(digits) < len(value[0:unit_start].strip()) and (
        not units or value[end:].strip().lower() not in [unt.lower() for unt in units]
    ):
        msg = f"{skipped} and u" if skipped else "U"
        return _Warning(
            msg=f"{msg}nexpected trailing characters: {value[end:]}",
            value=numeric_type(digits),
        )
    if skipped:
        return _Warning(msg=skipped, value=numeric_type(digits))

    try:
        return numeric_type(digits)
    except ValueError:
        if take_first is None:
            raise
        numeric = numeric_type(digits.split("-")[0 if take_first else -1])
        return _Warning(
            msg=f"Used {'first' if take_first else 'second'} value ({numeric}).",
            value=numeric,
        )


def to_float(value, units=None, prefixes=None, take_first=None):
    return to_numeric(
        numeric_type=float,
        value=value,
        units=units,
        prefixes=prefixes,
        take_first=take_first,
    )


def to_decimal_degrees(value):
    """
    Converts ISO6709 degrees minutes seconds into decimal degrees.
    :param value:
    :return:
    """
    flt = to_float(value)
    if isinstance(flt, _Warning):
        return _Warning(msg=flt.msg, value=dddmmssss_to_decimal(flt.value))
    if isinstance(flt, _Ignored):
        return flt
    return dddmmssss_to_decimal(to_float(value))


def to_int(value, units=None, prefixes=None):
    try:
        return to_numeric(numeric_type=int, value=value, units=units, prefixes=prefixes)
    except ValueError:
        from_float = to_numeric(
            numeric_type=float, value=value, units=units, prefixes=prefixes
        )
        return _Warning(
            msg="Value should be an integer.",
            value=int(
                from_float.value if isinstance(from_float, _Warning) else from_float
            ),
        )


def to_seconds(value):
    seconds = to_int(
        value, units=["sec", "second", "seconds", "s.", "s"], prefixes=["every"]
    )
    if isinstance(seconds, _Warning):
        low_val = value.lower()
        if "hour" in low_val or "hr" in low_val:
            seconds = seconds.value * 3600
            return _Warning(msg=f"Converted to {seconds} seconds!", value=seconds)
        elif "minute" in low_val or "min" in low_val:
            seconds = seconds.value * 60
            return _Warning(msg=f"Converted to {seconds} seconds!", value=seconds)
    return seconds


def to_pressure(value):
    hpa = to_float(
        value, units=["%", "hPa", "% hPa"], prefixes=ACCURACY_PREFIXES, take_first=False
    )
    if isinstance(hpa, _Warning):
        low_val = value.lower()
        if "mb" in low_val or "mbar" in low_val:
            hpa = hpa.value * 100
            return _Warning(msg=f"Converted to {hpa:0.01f} hPa", value=hpa)
        if "mm" in low_val:
            hpa = hpa.value * 133.3
            return _Warning(msg=f"Converted to {hpa:0.01f} hPa", value=hpa)
    return hpa


def _to_date(value):
    if value.strip():
        if "CCYY-MM-DD" in value.upper():
            return _Ignored(msg=f"{value} is a placeholder.")
        try:
            return parse_date(value, tzinfos=TZ_INFOS).date()
        except Exception as exc:
            raise ValueError(
                f"Unable to parse {value} into a date. Expected format: CCYY-MM-DD"
            ) from exc
    return None


def _to_datetime(value):
    if value.strip():
        if "CCYY-MM-DD" in value.upper():
            return _Ignored(msg=f"{value} is a placeholder.")
        try:
            # UT and UTUT has been seen as a timezone specifier in the wild
            dt = parse_date(value, tzinfos=TZ_INFOS)
            if not dt.tzinfo or dt.tzinfo == tzlocal():
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception as exc:
            raise ValueError(
                f"Unable to parse {value} into a date and time. Expected "
                f"format: CCYY-MM-DDThh:mmZ"
            ) from exc
    return None


to_date = partial(try_prefixes, converter=_to_date)
to_datetime = partial(try_prefixes, converter=_to_datetime)


def to_point(x, y, z):
    if x is None or y is None or z is None:
        return None
    return Point(x, y, z)


def to_alignment(value):
    try:
        return to_float(value, units=["deg", "degrees"])
    except ValueError:
        if "true north" in value.lower():
            return _Warning(msg="Interpreted as zero.", value=0)
        raise


def to_str(value):
    if value is None:
        return ""
    return value


def concat_str(value):
    """
    For multi-line inputs, concatenate the lines, stripping white space at each line
    break. This is necessary for things like multi-line urls.
    """
    if value is None:
        return ""
    return "".join([ln.strip() for ln in value.splitlines()])


class BaseBinder:
    parsed: BaseParser = None

    @property
    def lines(self) -> List[str]:
        return self.parsed.lines

    @property
    def findings(self):
        return self.parsed.findings

    def __init__(self, parsed: BaseParser):
        self.parsed = parsed
