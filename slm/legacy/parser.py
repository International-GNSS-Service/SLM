"""
This file contains parsing logic for the legacy Site Log format, such as one
exists. It makes no assumptions about what sections/parameters should be
present - it simply parses out sections, parameters and parameter values.

The next phase of site log interpretation is referred to as "binding" - this
is where the expected values are found and validated. Binding significantly
depends on the rest of the SLM code base and for that reason, is done
externally to this file - which should remain a data-naive process focused
only on syntax.

..note::
    Please do not import any SLM specific code into this parser. The goal is to
    keep this parser as a standalone legacy site log format parser that can
    be pulled out of the SLM source tree and used in other contexts.
"""
import re
from typing import (
    Union,
    List,
    Optional,
    Dict,
    Tuple
)
from datetime import date, datetime


SPECIAL_CHARACTERS = '().,-_[]{}<>+%'


class SubHeading:

    name = ''
    active = False

    def __init__(self, name=name, active=active):
        self.name = name
        self.active = active


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

    @property
    def mismatch(self):
        return self.line.strip() != self.parser.lines[self.lineno].strip()

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


class ParsedParameter:

    REGEX = re.compile(
        rf'\s+([\w\s/().,_<>+%-]+)\s+:\s*(.*)?'
    )
    REGEX_MULTI = re.compile(
        r'\s+:\s+(.*)?'
    )

    REGEX_PLACEHOLDER = re.compile(
        r'\([^()]+\)'
    )

    name = ''
    parser = None
    section = None
    line_no = None
    line_end = None
    values = None

    binding = None

    @property
    def is_placeholder(self):
        return bool(
            self.REGEX_PLACEHOLDER.fullmatch(
                self.value.replace('\n', '')
            )
        )

    @property
    def is_empty(self):
        return not self.value.strip()

    @property
    def num_lines(self):
        return self.line_end - self.line_no + 1

    @property
    def lines(self):
        return self.parser.lines[self.line_no:self.line_end]
    
    def __init__(self, line_no, match, parser, section, sub_heading=''):
        self.line_no = line_no
        self.line_end = line_no
        self.parser = parser
        self.section = section
        self.name = f'{sub_heading if sub_heading else ""}' \
                    f'{"::" if sub_heading else ""}' \
                    f'{match.group(1).strip()}'
        self.values = [match.group(2).strip()]
        if self.is_placeholder:
            self.parser.add_finding(
                Ignored(
                    self.line_no,
                    self,
                    'Placeholder text',
                    match.group(0)
                )
            )

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


class ParsedSection:

    REGEX = re.compile(
        r'([0-9]+)[.](?:([0-9xX]+)[.]?)?(?:([0-9xX]+)[.]?)?\s+([\w\s().,-]+)?'
    )

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

    _param_binding_: Dict[str, ParsedParameter] = None
    _binding_: Dict[str, Union[str, int, float, date, datetime]] = None

    def get_param(self, name: str) -> Optional[ParsedParameter]:
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

    def __init__(self, line_no, match, parser):
        self.parameters = {}
        self.line_no = line_no
        self.line_end = line_no
        self.lines = [match.group(0)]
        self.section_number = int(match.group(1))
        self.parser = parser
        if match.group(3):
            self.subsection_number = match.group(2)
            self.order = match.group(3)
        elif match.group(2):
            self.subsection_number = match.group(2)

        if match.group(4):
            self.header = match.group(4).strip()

        if (
            isinstance(self.subsection_number, str) and
                self.subsection_number.isdigit()
        ):
            self.subsection_number = int(self.subsection_number)
        elif match.group(2):
            self.example = True

        if isinstance(self.order, str) and self.order.isdigit():
            self.order = int(self.order)
        elif match.group(3):
            self.example = True

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


class SiteLogParser:
    """
    This is a VERY lenient parser. SLM will never publish a submitted site log
    without reformatting it, so the main goal here is to make a best-effort
    parsing of the log and provide some deep introspective output on what the
    parsing recorded.
    """

    lines: Optional[List[str]]
    
    # all non-parameter, section header or graphic lines we expect to see
    # in site log files - we ignore these. If not in this set and it's not
    # one of the above a warning will be logged
    IGNORED_LINES = {
        normalize('If Update:'),
        normalize('Approximate Position (ITRF)'),
        normalize(
            'Differential Components from GNSS Marker to the tied monument '
            '(ITRS)'
        ),
        normalize('Hardcopy on File'),
        normalize(
            'Antenna Graphics with Dimensions'
        ),
        normalize(
            '(insert text graphic from file antenna.gra)'
        )
    }

    SUB_HEADINGS = {
        normalize('Primary Contact'),
        normalize('Secondary Contact')
    }

    SECTION_BREAKERS = [
        normalize('Additional Information'),
        normalize('Notes')
    ]

    """
    Sections indexed by section number tuple 
    (section_number, subsection_number, order)
    """
    sections: Dict[
        Tuple[int, Optional[int], Optional[int]],
        ParsedSection
    ]

    graphic: str = None
    name_matched: bool = None
    site_name: str = None

    _findings_: Dict[int, Finding]

    # used to figure out where antenna graphic begins
    _graphic_start_: int

    _last_indent_: Optional[int] = None

    # last subheading observed and true if activated
    _sub_heading_: SubHeading = SubHeading('', False)
    
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

    def remove_finding(self, lineno):
        if lineno in self._findings_:
            del self._findings_[lineno]

    def add_finding(self, finding):
        if not isinstance(finding, Finding):
            raise ValueError(
                f'add_finding() expected a {Finding.__class__.__name__} '
                f'object, was given: {finding.__class__.__name__}.'
            )
        
        self._findings_[finding.lineno] = finding

    def add_section(self, section):
        if not section.example and section.contains_values:
            if section.index_tuple in self.sections:
                self.duplicate_section_error(section)
            self.sections[section.index_tuple] = section

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

    def __init__(
            self,
            site_log: Union[str, List[str]],
            site_name: str = None
    ) -> None:
        """
        Parse the ASCII Site Log format into model instances.

        :param site_log: The entire site log contents as a string or as a list
            of lines
        :param site_name: The expected 9-character site name of this site or
            None (default) if name is unknown
        """
        self._findings_ = {}
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
        idx = 0
        while idx < len(self.lines):
            idx = self.visit_line(idx, self.lines[idx].strip())

        # the only way to be sure where the graphic is, is to rewind from the
        # end to the last encountered - removing any warnings/errors
        for finding in reversed(sorted(self.findings.keys())):
            if finding >= self._graphic_start_:
                self.remove_finding(finding)

        if self._graphic_start_ < len(self.lines):
            self.graphic = self.lines[self._graphic_start_:]

            # chop beginning and ending empty lines off
            begin = None
            end = None
            for indexes in [
                range(0, len(self.graphic) - 1),
                reversed(range(0, len(self.graphic) - 1))
            ]:
                for idx in indexes:
                    if self.graphic[idx].strip():
                        if begin is None:
                            begin = idx
                        elif end is None:
                            end = idx+1
                        break
                    # self.add_finding(
                    #    Ignored(
                    #        self._graphic_start_+idx,
                    #        self,
                    #        'Empty line',
                    #        line=self.graphic[idx]
                    #    )
                    # )

            self.graphic = '\n'.join(self.graphic[begin:end])
        
    def visit_line(self, idx, line):
        if not line.strip():  # skip empty lines
            #self.add_finding(Ignored(idx, self, 'Empty line', line=line))
            return idx + 1

        match = ParsedSection.REGEX.match(line)  # is this a section header?
        if match:
            section = ParsedSection(idx, match, self)
            lineno = self.visit_section(
                idx+1,
                self.lines[idx],
                section
            )
            self.add_section(section)
            if section.example:
                for ex_ln in range(section.line_no, section.line_end):
                    self.add_finding(
                        Ignored(
                            ex_ln,
                            self,
                            'Placeholder text',
                            self.lines[ex_ln]
                        )
                    )
            self._sub_heading_ = SubHeading(name='', active=False)
            self._last_indent_ = None
            return lineno
        elif (
            len(self.sections) > 0 and  # ignore lines before the first section
            normalize(line) not in self.IGNORED_LINES
        ):
            self.add_finding(Warn(idx, self, 'Unrecognized line', line=line))
        else:
            # look for the site name in the header somewhere before the first
            # section.
            self._graphic_start_ = idx + 1
            if self.name_matched is None:
                if (
                    self.site_name is not None and
                    self.site_name in line.upper()
                ):
                    self.name_matched = True
                    return idx + 1
                elif (
                    'site' in line.lower() and
                    'info' in line.lower() and
                    len(line.split()[0]) in {4, 9}
                ):
                    self.name_matched = False if self.site_name else None
                    if self.name_matched is False:
                        self.add_finding(
                            Error(
                                idx,
                                self,
                                f'Incorrect site name: {self.site_name}'
                            )
                        )
                    self.site_name = line.split()[0].upper()
                    return idx + 1

            # self.add_finding(Ignored(idx, self, 'Non-data line', line=line))
        return idx + 1

    def visit_section(self, idx, line, section):
        # first line is a special case - could have data and could
        # be multi line!
        idx += self.visit_section_line(
            idx-1,
            f'{line.strip().lstrip(section.index_string)} ',
            section,
            header_line=True
        ) - 1
        while (
            idx < len(self.lines)
            and not ParsedSection.REGEX.match(self.lines[idx].strip())
        ):
            for section_breaker in self.SECTION_BREAKERS:
                if section_breaker in section.parameters:
                    return idx

            line = self.lines[idx]
            section.lines.append(line)
            lines_parsed = self.visit_section_line(
                idx, line, section
            )
            idx += lines_parsed

        return idx

    def visit_section_line(self, idx, line, section, header_line=False):
        line_no = 1
        if not line.strip():  # ignore empty lines
            # self.add_finding(Ignored(idx, self, 'Empty line', line=line))
            return line_no

        if not header_line:
            indent = self.count_indent(line)
            if self._last_indent_ is not None:
                if indent > self._last_indent_:
                    self._sub_heading_.active = True
                elif indent < self._last_indent_:
                    self._sub_heading_.name = ''
                    self._sub_heading_.active = False
                elif not self._sub_heading_.active:
                    self._sub_heading_.name = ''

            self._last_indent_ = indent

        match = ParsedParameter.REGEX.fullmatch(line)
        if match:
            parameter = ParsedParameter(
                idx,
                match,
                self,
                section,
                sub_heading=self._sub_heading_.name
                if self._sub_heading_.active else ''
            )
            self._graphic_start_ = idx + 1
            while idx+line_no < len(self.lines):
                if self.lines[idx+line_no].strip():
                    match = ParsedParameter.REGEX_MULTI.match(
                        self.lines[idx+line_no]
                    )
                    if not match:
                        break
                    parameter.append(idx+line_no, match)
                    self._graphic_start_ = idx + line_no + 1
                else:
                    pass
                    # self.add_finding(
                    #    Ignored(
                    #        idx+line_no,
                    #        self,
                    #        'Empty line',
                    #        line=line
                    #    )
                    # )
                line_no += 1
            section.add_parameter(parameter)
        elif not header_line:
            if normalize(line) in self.IGNORED_LINES:
                pass
                # self.add_finding(
                #     Ignored(idx, self, 'Non-data line', line=line)
                # )
            elif normalize(line) in self.SUB_HEADINGS:
                self._sub_heading_.name = normalize(line)
            else:
                self.add_finding(
                    Warn(idx, self, 'Unrecognized line', line=line)
                )

        return line_no

    @property
    def is_valid(self):
        return len(self.errors) == 0

    @property
    def has_warnings(self):
        return len(self.warnings) == 0

    def count_indent(self, line):
        count = 0
        for char in line:
            if char == ' ':
                count += 1
            elif char == '\t':
                count += 4
            else:
                break
        return count
