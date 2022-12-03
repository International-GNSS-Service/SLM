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


SPECIAL_CHARACTERS = '().,-_[]{}<>+%'


def normalize(name):
    """
    Normalization is designed to remove any superficial variable name
    mismatches. We remove all special characters and spaces and then
    upper case the name.
    """
    for char in SPECIAL_CHARACTERS + ' \t':
        name = name.replace(char, '')
    return name.upper()


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
    pass


class Error(Finding):
    pass


class Warn(Finding):
    pass


class ParsedParameter:

    REGEX = re.compile(
        r'\s+([\w\s/().,_<>+-]+)\s+:\s*(.*)?'
    )
    REGEX_MULTI = re.compile(
        r'\s+:\s+(.*)?'
    )

    REGEX_PLACEHOLDER = re.compile(
        r'\([^()]+\)'
    )

    name = ''
    parser = None
    line_no = None
    line_end = None
    values = None

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
    
    def __init__(self, line_no, match, parser):
        self.line_no = line_no
        self.line_end = line_no
        self.parser = parser
        self.name = match.group(1).strip()
        self.values = [match.group(2).strip()]

    def append(self, line_no, match):
        self.line_end = line_no
        self.values.append(match.group(1).strip())

    @property
    def value(self):
        return '\n'.join(self.values)

    @property
    def normalized_name(self):
        return normalize(self.name)

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
    major = None
    minor = None
    subsection = None
    header = ''

    """{
        str(normalized name): str(value)
    }
    """
    parameters = None
    example = False

    def __init__(self, line_no, match, parser):
        self.parameters = {}
        self.line_no = line_no
        self.line_end = line_no
        self.lines = [match.group(0)]
        self.major = int(match.group(1))
        self.parser = parser
        if match.group(3):
            self.minor = match.group(2)
            self.subsection = match.group(3)
        elif match.group(2):
            self.minor = match.group(2)

        if match.group(4):
            self.header = match.group(4).strip()

        if isinstance(self.minor, str) and self.minor.isdigit():
            self.minor = int(self.minor)
        elif match.group(2):
            self.example = True

        if isinstance(self.subsection, str) and self.subsection.isdigit():
            self.subsection = int(self.subsection)
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
        index = f'{self.major}'
        if self.minor or self.example:
            index += f'.{self.minor if self.minor else "x"}'
            if self.minor and (self.subsection or self.example):
                index += f'.{self.subsection if self.subsection else "x"}'
        return index

    @property
    def index_tuple(self):
        return self.major, self.minor, self.subsection

    def add_parameter(self, parameter):
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

    lines = None
    
    _findings_ = {}

    # used to figure out where antenna graphic begins
    _graphic_start_ = None
    
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
        normalize('Primary Contact'),
        normalize('Secondary Contact'),
        normalize('Hardcopy on File'),
        normalize(
            'Antenna Graphics with Dimensions'
        ),
        normalize(
            '(insert text graphic from file antenna.gra)'
        )
    }

    SECTION_BREAKERS = [
        normalize('Additional Information'),
        normalize('Notes')
    ]

    """
    Sections indexed by section number
    """
    sections = None

    graphic = None
    
    @property
    def findings(self):
        """
        Return findings dictionary keyed by line number and ordered by
        line number.
        """
        # dictionaries are ordered in python 3.7+
        return dict(sorted(self._findings_.items()))

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

    def __init__(self, site_log):
        """
        Parse the ASCII Site Log format into model instances.

        :param site_log: The entire site log contents as a string or as a list
            of lines
        """
        self.sections = {}
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
                    self.add_finding(
                        Ignored(
                            self._graphic_start_+idx,
                            self,
                            'Empty line',
                            line=self.graphic[idx]
                        )
                    )

            self.graphic = '\n'.join(self.graphic[begin:end])
        
    def visit_line(self, idx, line):
        if not line.strip():  # skip empty lines
            self.add_finding(Ignored(idx, self, 'Empty line.', line=line))
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
            return lineno
        elif (
            len(self.sections) > 0 and  # ignore lines before the first section
            normalize(line) not in self.IGNORED_LINES
        ):
            self.add_finding(Warn(idx, self, 'Unrecognized line', line=line))
        else:
            self._graphic_start_ = idx + 1
            self.add_finding(Ignored(idx, self, 'Non-data line', line=line))
        return idx+1

    def visit_section(self, idx, line, section):
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

    def visit_section_line(self, idx, line, section):
        line_no = 1
        if not line.strip():  # ignore empty lines
            self.add_finding(Ignored(idx, self, 'Empty line..', line=line))
            return line_no
        match = ParsedParameter.REGEX.fullmatch(line)
        if match:
            parameter = ParsedParameter(idx, match, self)
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
                    self.add_finding(
                        Ignored(
                            idx+line_no,
                            self,
                            'Empty line...',
                            line=line
                        )
                    )
                line_no += 1
            section.add_parameter(parameter)

        elif normalize(line) not in self.IGNORED_LINES:
            self.add_finding(Warn(idx, self, 'Unrecognized line', line=line))
        else:
            self.add_finding(Ignored(idx, self, 'Non-data line.', line=line))

        return line_no

    @property
    def is_valid(self):
        return len(self.errors) == 0

    @property
    def has_warnings(self):
        return len(self.warnings) == 0
