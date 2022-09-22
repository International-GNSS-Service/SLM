from slm.models import Site
import re


class Finding:

    def __init__(self, index, line, message):
        self.index = index
        self.line = line
        self.message = message

    def __str__(self):
        return f'{self.message} -> ({self.index}): {self.line}'


class Error(Finding):

    def __str__(self):
        return f'[ERROR] {super().__str__()}'


class Warning(Finding):

    def __str__(self):
        return f'[WARNING] {super().__str__()}'


class CanonicalSection:

    major = None
    minor = None
    subsection = None
    header = None

    def __init__(self, header, major, minor=None, subsection=None):
        pass


class CanonicalVariable:
    pass


class ParsedSection:

    REGEX = re.compile(
        r'([0-9]+)[.](?:([0-9xX]+)[.](?:([0-9xX]+)[.]?)?)?\s+(\w+)?'
    )

    idx = None
    major = None
    minor = None
    subsection = None
    header = ''
    lines = []
    example = False

    def __init__(self, idx, match):
        self.idx = idx
        self.lines = [match.group(0)]
        self.major = int(match.group(1))
        if match.group(3):
            self.minor = match.group(2)
            self.subsection = match.group(3)
        elif match.group(2):
            self.subsection = match.group(2)

        if match.group(4):
            self.header = match.group(4)

        if isinstance(self.minor, str) and self.minor.isdigit():
            self.minor = int(self.minor)
        else:
            self.example = True

        if isinstance(self.subsection, str) and self.subsection.isdigit():
            self.subsection = int(self.subsection)
        else:
            self.example = True


class ParsedLine:
    pass


class SiteLogParser:

    lines = None
    sites = Site.objects
    errors = []
    warnings = []

    def __init__(self, site_log, sites=sites):
        """
        Parse the ASCII Site Log format into model instances.

        :param site_log:
        """
        self.lines = site_log.split('\n')
        idx = 0
        while idx < len(self.lines):
            idx = self.visit_line(idx, self.lines[idx].strip())

    def visit_line(self, idx, line):
        if not line:
            return idx + 1
        match = ParsedSection.REGEX.fullmatch(line)
        if match:
            return self.visit_section(
                idx+1,
                self.lines[idx],
                ParsedSection(idx, match)
            )
        else:
            self.warnings.append(Warning(idx, line, 'Unrecognized line'))
            return idx + 1

    def visit_section(self, idx, line, section):
        while (
            idx < len(self.lines)
            and not ParsedSection.REGEX.fullmatch(self.lines[idx].strip())
        ):
            line = self.lines[idx]
            idx += 1
            section.lines.append(line)
            if not section.example:
                idx += self.visit_section_line(idx, line, section)

        return idx

    def visit_section_line(self, idx, line, section):
        pass

    @property
    def is_valid(self):
        return len(self.errors) == 0

    @property
    def has_warnings(self):
        return len(self.warnings) == 0
