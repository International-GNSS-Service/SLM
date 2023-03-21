from typing import Dict, Optional, List, Union, Tuple
from datetime import date, datetime
from slm.models import (
    Antenna,
    Radome,
    Receiver,
    SatelliteSystem
)
from dateutil.parser import parse as parse_date
from slm.utils import dddmmssss_to_decimal


SPECIAL_CHARACTERS = '().,-_[]{}<>+%'
NUMERIC_CHARACTERS = {'.', '+', '-'}


def normalize(name):
    """
    Normalization is designed to remove any superficial variable name
    mismatches. We remove all special characters and spaces and then
    upper case the name.
    """
    for char in SPECIAL_CHARACTERS + ' \t':
        name = name.replace(char, '')
    return name.upper().strip()


class Finding:
    """
    A base class for parser/binding findings.
    """

    def __init__(
            self,
            lineno,
            parser,
            message,
            section=None,
            parameter=None,
            line=None
    ):
        self.lineno = lineno
        self.parser = parser
        self.message = message
        self.section = section
        self.parameter = parameter
        self.line = line

    def __str__(self):
        return f'({self.lineno+1: 4}) {self.parser.lines[self.lineno]}' \
               f'{" " * (80-len(self.parser.lines[self.lineno]))}' \
               f'[{self.level.upper()}]: {self.message}'

    @property
    def level(self):
        return self.__class__.__name__.lower()


class Ignored(Finding):

    level = 'I'


class Error(Finding):

    level = 'E'


class Warn(Finding):

    level = 'W'


class BaseParameter:

    name = ''
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
        return self.parser.lines[self.line_no:self.line_end]

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
        return '\n'.join(self.values)

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
            return f'{self.name} [PLACEHOLDER]: {self.value}'
        return f'{self.name}: {self.value}'


class BaseSection:

    line_no = None
    line_end = None
    section_number = None
    subsection_number = None
    order = None
    header = ''

    """{
        str(normalized name): str(value)
    }
    """
    parameters = None
    example = False

    _param_binding_: Dict[str, BaseParameter] = None
    _binding_: Dict[str, Union[str, int, float, date, datetime]] = None

    def get_param(self, name: str) -> Optional[BaseParameter]:
        """
        Get parameter by parsing or bound name.
        """
        if self._param_binding_ is None:
            self._param_binding_ = {}
        return self._param_binding_.get(
            name,
            self.parameters.get(normalize(name), None)
        )

    def bind(self, name, parameter, value):
        """
        Bind a parameter to the given name and value.
        """
        if self._binding_ is None:
            self._binding_ = {}
        if self._param_binding_ is None:
            self._param_binding_ = {}
        self._param_binding_[name] = parameter
        self._binding_[name] = value

    @property
    def binding(self) -> Optional[
        Dict[str, Union[str, int, float, date, datetime]]
    ]:
        return self._binding_

    @property
    def ordering_id(self):
        if self.order:
            return self.order
        if self.subsection_number:
            return self.subsection_number
        return None

    def __init__(
            self,
            line_no,
            section_number,
            subsection_number,
            order,
            parser
    ):
        self.parameters = {}
        self.line_no = line_no
        self.line_end = line_no
        self.section_number = section_number
        self.subsection_number = subsection_number
        self.order = order
        self.parser = parser

        if (
            isinstance(self.subsection_number, str) and
            self.subsection_number.isdigit()
        ):
            self.subsection_number = int(self.subsection_number)

        if isinstance(self.order, str) and self.order.isdigit():
            self.order = int(self.order)

    def __str__(self):
        section_str = f'{self.index_string} {self.header}\n'
        if self.example:
            section_str = f'{self.index_string} {self.header} (EXAMPLE)\n'
        for name, param in self.parameters.items():
            section_str += f'\t{param}\n'
        return section_str

    @property
    def contains_values(self):
        """
        True if any parameter in this section contains a real value that is
        not a placeholder.
        """
        for name, param in self.parameters.items():
            if not (param.is_empty or param.is_placeholder):
                return True
        return False

    @property
    def index_string(self):
        index = f'{self.section_number}'
        if self.subsection_number or self.example:
            index += f'.'
            if self.subsection_number:
                index += str(self.subsection_number)
            else:
                index += 'x'
            if self.subsection_number and (self.order or self.example):
                index += f'.{self.order if self.order else "x"}'
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
                    f'Duplicate parameter: {parameter.name}',
                    section=self
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
    sections: Dict[
        Tuple[int, Optional[int], Optional[int]],
        BaseSection
    ]

    @property
    def findings(self) -> Dict[int, Finding]:
        """
        Return findings dictionary keyed by line number and ordered by
        line number.
        """
        # dictionaries are ordered in python 3.7+
        return dict(sorted(self._findings_.items()))

    @property
    def findings_context(self) -> Dict[int, str]:
        return {
            int(line): (finding.level, finding.message)
            for line, finding in self.findings.items()
        }

    @property
    def context(self):
        return {
            'site': self.site_name,
            'findings': self.findings_context
        }

    @property
    def ignored(self):
        return {
            lineno: finding for lineno, finding in self._findings_.items()
            if isinstance(finding, Ignored)
        }

    @property
    def errors(self):
        return {
            lineno: finding for lineno, finding in self._findings_.items()
            if isinstance(finding, Error)
        }

    @property
    def warnings(self):
        return {
            lineno: finding for lineno, finding in self._findings_.items()
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
        for lineno in range(
                duplicate_section.line_no,
                duplicate_section.line_end
        ):
            self.add_finding(
                Error(
                    lineno,
                    self,
                    f'Duplicate section {duplicate_section.index_string}',
                    section=duplicate_section
                )
            )

    def add_finding(self, finding):
        if not isinstance(finding, Finding):
            raise ValueError(
                f'add_finding() expected a {Finding.__class__.__name__} '
                f'object, was given: {finding.__class__.__name__}.'
            )
        self._findings_[finding.lineno] = finding

    def __init__(
            self,
            site_log: Union[str, List[str]],
            site_name: str = None
    ) -> None:
        """
        :param site_log: The entire site log contents as a string or as a list
            of lines
        :param site_name: The expected 9-character site name of this site or
            None (default) if name is unknown
        """
        self.sections = {}
        self.site_name = site_name.upper() if site_name else site_name
        if isinstance(site_log, str):
            self.lines = site_log.split('\n')
        elif isinstance(site_log, list):
            self.lines = site_log
        else:
            raise ValueError(
                f'Expected site_log input to be string or list of lines, '
                f'given: {type(site_log)}.'
            )

        self._findings_ = {}


def to_antenna(value):
    antenna = value.strip()
    parts = value.split()
    if len(parts) > 1 and len(antenna) > 16:
        antenna = value.rstrip(parts[-1]).strip()
    try:
        return Antenna.objects.get(model__iexact=antenna).model
    except Antenna.DoesNotExist:
        antennas = '\n'.join(
            [ant.model for ant in Antenna.objects.all()]
        )
        raise ValueError(
            f"Unexpected antenna model {antenna}. Must be one of "
            f"\n{antennas}"
        )


def to_radome(value):
    radome = value.strip()
    try:
        return Radome.objects.get(model__iexact=radome).model
    except Radome.DoesNotExist:
        radomes = '\n'.join(
            [rad.model for rad in Radome.objects.all()]
        )
        raise ValueError(
            f"Unexpected radome model {radome}. Must be one of "
            f"\n{radomes}"
        )


def to_receiver(value):
    receiver = value.strip()
    try:
        return Receiver.objects.get(model__iexact=receiver).model
    except Receiver.DoesNotExist:
        receivers = '\n'.join(
            [rec.model for rec in Receiver.objects.all()]
        )
        raise ValueError(
            f"Unexpected receiver model {receiver}. Must be one of "
            f"\n{receivers}"
        )


def to_satellites(value):
    sats = []
    bad_sats = set()
    for sat in [sat for sat in value.split('+') if sat]:
        try:
            sats.append(SatelliteSystem.objects.get(name__iexact=sat).pk)
        except SatelliteSystem.DoesNotExist:
            bad_sats.add(sat)
    if bad_sats:
        bad_sats = '  \n'.join(bad_sats)
        good_sats = '  \n'.join(
            [sat.name for sat in SatelliteSystem.objects.all()]
        )
        raise ValueError(
            f"Expected constellation list delineated by '+' (e.g. GPS+GLO). "
            f"Unexpected values encountered: \n{bad_sats}\n\nMust be one of "
            f"\n{good_sats}"
        )
    return sats


def to_enum(enum_cls, value, strict=True, blank=None):
    if value:
        try:
            return enum_cls(value).value
        except ValueError as ve:
            if not strict:
                return value.strip()
            valid_list = "  \n".join(en.label for en in enum_cls)
            raise ValueError(
                f'Invalid value {value} must be one of:\n'
                f'{valid_list}'
            ) from ve
    return blank


def to_numeric(numeric_type, value):
    """
    The strategy for converting string parameter values to numerics is to chop
    the numeric off the front of the string. If there's any more numeric
    characters in the remainder its an error.
    """
    if not value:
        return None

    # just try to chop the numbers off the front of the string
    digits = ''
    for char in value:
        if char.isdigit() or char in NUMERIC_CHARACTERS:
            digits += char

    if not digits:
        raise ValueError(
            f'Could not convert {value} to type {numeric_type.__name__}.'
        )

    # there should not be any other numbers in the string!
    for char in value.replace(digits, ''):
        if char.isdigit():
            raise ValueError(
                f'Could not convert {value} to type {numeric_type.__name__}.'
            )

    return numeric_type(digits)


def to_float(value):
    return to_numeric(numeric_type=float, value=value)


def to_decimal_degrees(value):
    """
    Converts ISO6709 degrees minutes seconds into decimal degrees.
    :param value:
    :return:
    """
    return dddmmssss_to_decimal(to_float(value))


def to_int(value):
    return to_numeric(numeric_type=int, value=value)


def to_date(value):
    if value.strip():
        if 'CCYY-MM-DD' in value.upper():
            return None
        try:
            return parse_date(value).date()
        except:
            raise ValueError(
                f'Unable to parse {value} into a date. Expected '
                f'format: CCYY-MM-DD'
            )
    return None


def to_datetime(value):
    if value.strip():
        if 'CCYY-MM-DD' in value.upper():
            return None
        try:
            return parse_date(value)
        except:
            raise ValueError(
                f'Unable to parse {value} into a date and time. Expected '
                f'format: CCYY-MM-DDThh:mmZ'
            )
    return None


def to_str(value):
    if value is None:
        return ''
    return value


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
