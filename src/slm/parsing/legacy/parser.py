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
from typing import List, Optional, Union

from slm.parsing import (
    BaseParameter,
    BaseParser,
    BaseSection,
    Error,
    Ignored,
    Warn,
    normalize,
)


class SubHeading:
    name = ""
    active = False

    def __init__(self, name=name, active=active):
        self.name = name
        self.active = active


class ParsedParameter(BaseParameter):
    REGEX = re.compile(r"\s*([\w\s/().,_<>+%-]+)\s*:\s*(.*)?")
    REGEX_MULTI = re.compile(r"\s+:\s+(.*)?")

    REGEX_PLACEHOLDER = re.compile(r"\([^()]+\)")

    @property
    def is_placeholder(self):
        return bool(self.REGEX_PLACEHOLDER.fullmatch(self.value.replace("\n", "")))

    def __init__(self, line_no, match, parser, section, sub_heading=""):
        super().__init__(
            line_no=line_no,
            name=(
                f"{sub_heading if sub_heading else ''}"
                f"{'::' if sub_heading else ''}"
                f"{match.group(1).strip()}"
            ),
            values=[match.group(2).strip()],
            parser=parser,
            section=section,
        )
        if self.is_placeholder:
            self.parser.add_finding(
                Ignored(self.line_no, self.parser, "Placeholder text", match.group(0))
            )


class ParsedSection(BaseSection):
    REGEX = re.compile(
        r"([0-9]+)[.](?:([0-9xX]+)[.]?)?(?:([0-9xX]+)[.]?)?\s*([\w\s().,-]+)?"
    )

    line_no = None
    line_end = None
    section_number = None
    subsection_number = None
    order = None
    header = ""

    """{
        str(normalized name): str(value)
    }
    """
    parameters = None
    example = False

    @property
    def ordering_id(self):
        if self.order:
            return self.order
        if self.subsection_number:
            return self.subsection_number
        return None

    def __init__(self, line_no, match, parser):
        super().__init__(
            line_no=line_no,
            section_number=int(match.group(1)),
            subsection_number=match.group(2),
            order=match.group(3),
            parser=parser,
        )
        self.lines = [match.group(0)]
        self.example = (
            not isinstance(self.subsection_number, int) and match.group(2)
        ) or (not isinstance(self.order, int) and match.group(3))

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


class SiteLogParser(BaseParser):
    """
    This is a VERY lenient parser. SLM will never publish a submitted site log
    without reformatting it, so the main goal here is to make a best-effort
    parsing of the log and provide some deep introspective output on what the
    parsing recorded.
    """

    # all non-parameter, section header or graphic lines we expect to see
    # in site log files - we ignore these. If not in this set and it's not
    # one of the above a warning will be logged
    IGNORED_LINES = {
        normalize("If Update:"),
        normalize("Approximate Position"),
        normalize("Approximate Position (ITRF)"),
        normalize(
            "Differential Components from GNSS Marker to the tied monument (ITRS)"
        ),
        normalize("Hardcopy on File"),
        normalize("Antenna Graphics with Dimensions"),
        normalize("(insert text graphic from file antenna.gra)"),
    }

    SUB_HEADINGS = {normalize("Primary Contact"), normalize("Secondary Contact")}

    SECTION_BREAKERS = [normalize("Additional Information"), normalize("Notes")]

    graphic: str = None

    # used to figure out where antenna graphic begins
    _graphic_start_: int

    _last_indent_: Optional[int] = None

    # last subheading observed and true if activated
    _sub_heading_: SubHeading = SubHeading("", False)

    def __init__(self, site_log: Union[str, List[str]], site_name: str = None) -> None:
        """
        Parse the ASCII Site Log format into data structures.

        :param site_log: The entire site log contents as a string or as a list
            of lines
        :param site_name: The expected 9-character site name of this site or
            None (default) if name is unknown
        """
        super().__init__(site_log=site_log, site_name=site_name)

        idx = 0
        while idx < len(self.lines):
            idx = self.visit_line(idx, self.lines[idx].strip())

        # throw an error if we didnt match the expected name
        if self.name_matched is False and self.site_name:
            self.add_finding(Error(0, self, f"Expected site name: {self.site_name}"))

        # the only way to be sure where the graphic is, is to rewind from the
        # end to the last encountered - removing any warnings/errors
        for finding in reversed(sorted(self.findings.keys())):
            if finding >= self._graphic_start_:
                self.remove_finding(finding)

        if self._graphic_start_ < len(self.lines):
            self.graphic = self.lines[self._graphic_start_ :]

            # chop beginning and ending empty lines off
            begin = None
            end = None
            for indexes in [
                range(0, len(self.graphic) - 1),
                reversed(range(0, len(self.graphic) - 1)),
            ]:
                for idx in indexes:
                    if self.graphic[idx].strip():
                        if begin is None:
                            begin = idx
                        elif end is None:
                            end = idx + 1
                        break
                    # self.add_finding(
                    #    Ignored(
                    #        self._graphic_start_+idx,
                    #        self,
                    #        'Empty line',
                    #        line=self.graphic[idx]
                    #    )
                    # )

            self.graphic = "\n".join(self.graphic[begin:end])

    def visit_line(self, idx, line):
        if not line.strip():  # skip empty lines
            # self.add_finding(Ignored(idx, self, 'Empty line', line=line))
            return idx + 1

        match = ParsedSection.REGEX.match(line)  # is this a section header?
        if match:
            section = ParsedSection(idx, match, self)
            lineno = self.visit_section(idx + 1, self.lines[idx], section)
            self.add_section(section)
            if section.example:
                for ex_ln in range(section.line_no, section.line_end):
                    self.add_finding(
                        Ignored(ex_ln, self, "Placeholder text", self.lines[ex_ln])
                    )
            self._sub_heading_ = SubHeading(name="", active=False)
            self._last_indent_ = None
            return lineno
        elif (
            len(self.sections) > 0  # ignore lines before the first section
            and normalize(line) not in self.IGNORED_LINES
        ):
            self.add_finding(Warn(idx, self, "Unrecognized line", line=line))
        else:
            # look for the site name in the header somewhere before the first
            # section.
            self._graphic_start_ = idx + 1
            if self.name_matched is None:
                if self.site_name is not None and (
                    self.site_name.upper() in line.upper()
                    or f"{self.site_name[0:4].upper()} " in line.upper()
                ):
                    self.name_matched = True
                    header_site_name = line.split()[0].upper()
                    if self.site_name.upper() in header_site_name:
                        self.site_name = header_site_name
                    return idx + 1
                elif (
                    "site" in line.lower()
                    and "info" in line.lower()
                    and 4 <= len(line.split()[0]) <= 9
                ):
                    self.name_matched = False if self.site_name else None
                    if self.name_matched is False:
                        self.add_finding(
                            Error(idx, self, f"Incorrect site name: {line.split()[0]}")
                        )
                    self.site_name = line.split()[0].upper()
                    return idx + 1

            # self.add_finding(Ignored(idx, self, 'Non-data line', line=line))
        return idx + 1

    def visit_section(self, idx, line, section):
        # first line is a special case - could have data and could
        # be multi line!
        idx += (
            self.visit_section_line(
                idx - 1,
                f"{line.strip().lstrip(section.index_string)} ",
                section,
                header_line=True,
            )
            - 1
        )
        while idx < len(self.lines) and not ParsedSection.REGEX.match(
            self.lines[idx].strip()
        ):
            for section_breaker in self.SECTION_BREAKERS:
                # TODO - shouldn't break section if not an *expected* param - see MOIN00CRI
                if section_breaker in section.parameters:
                    return idx

            line = self.lines[idx]
            section.lines.append(line)
            lines_parsed = self.visit_section_line(idx, line, section)
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
                    self._sub_heading_.name = ""
                    self._sub_heading_.active = False
                elif not self._sub_heading_.active:
                    self._sub_heading_.name = ""

            self._last_indent_ = indent

        match = ParsedParameter.REGEX.fullmatch(line)
        if match:
            parameter = ParsedParameter(
                idx,
                match,
                self,
                section,
                sub_heading=(
                    self._sub_heading_.name if self._sub_heading_.active else ""
                ),
            )
            self._graphic_start_ = idx + 1
            while idx + line_no < len(self.lines):
                if self.lines[idx + line_no].strip():
                    match = ParsedParameter.REGEX_MULTI.match(self.lines[idx + line_no])
                    if not match:
                        break
                    parameter.append(idx + line_no, match)
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
                self.add_finding(Warn(idx, self, "Unrecognized line", line=line))

        return line_no

    def count_indent(self, line):
        count = 0
        for char in line:
            if char == " ":
                count += 1
            elif char == "\t":
                count += 4
            else:
                break
        return count
