import re
from functools import partial
from typing import Any, Callable, Dict, List, Tuple, Union

from django.utils.translation import gettext as _

from slm.defines import (
    AntennaReferencePoint,
    Aspiration,
    CollocationStatus,
    FractureSpacing,
    FrequencyStandardType,
    ISOCountry,
    TectonicPlates,
)
from slm.models import SatelliteSystem
from slm.parsing import (
    ACCURACY_PREFIXES,
    METERS,
    BaseBinder,
    Finding,
    _Ignored,
    _Warning,
    concat_str,
    remove_from_start,
    to_alignment,
    to_antenna,
    to_date,
    to_datetime,
    to_decimal_degrees,
    to_enum,
    to_float,
    to_point,
    to_pressure,
    to_radome,
    to_receiver,
    to_satellites,
    to_seconds,
    to_str,
)
from slm.parsing.legacy.parser import (
    Error,
    Ignored,
    ParsedSection,
    SiteLogParser,
    Warn,
    normalize,
)

TEMP_RANGE_REGEX = re.compile(
    r"(\d+(?:[.]\d*)?)[\s()°degrsDEGRSCc]*(?:(?:-)|(?:to))\s*"
    r"(\d+(?:[.]\d*)?)[\s()°degrsDEGRSCc]*"
)
TEMP_STAB_REGEX = re.compile(
    r"(\d+(?:[.]\d*)?)?[\s()°degrsDEGRSCc]*(?:(?:±)|"
    r"(?:\+/?-))?\s*(\d+(?:[.]\d*)?)?[\s()°degrsDEGRSCc]*"
)

DATE_PLACEHOLDERS = ["CCYY-MM-DD", "DD-MMM-YYYY"]

TEMP_STAB_PREFIXES = ["Tolerance = ", "Tolerance", "=", "~"]

param_registry = {}


def reg(name, header_index, bindings):
    for binding in [bindings] if isinstance(bindings, tuple) else bindings:
        param_registry.setdefault(header_index, {})[binding[0]] = name
    return normalize(name)


def ignored(_, msg=""):
    if msg:
        return _Ignored(msg)
    return _Ignored()


def to_temp_stab(value):
    value = remove_from_start(value, TEMP_STAB_PREFIXES)
    value = value.replace("º", "") if value else value
    if value.strip().lower() == "none":
        return False, None, None

    def get_tuple():
        nominal = None
        deviation = None
        if value:
            range_mtch = TEMP_RANGE_REGEX.match(value)
            if range_mtch:
                v1 = float(range_mtch.group(1))
                v2 = float(range_mtch.group(2))
                return True, (v1 + v2) / 2, abs(v1 - v2) / 2

            deviation_mtch = TEMP_STAB_REGEX.match(value)
            if deviation_mtch:
                nominal = (
                    float(deviation_mtch.group(1)) if deviation_mtch.group(1) else None
                )
                deviation = (
                    float(deviation_mtch.group(2)) if deviation_mtch.group(2) else None
                )

        if deviation is None and nominal is not None and nominal <= 10:
            deviation = nominal
            nominal = None

        return (
            (nominal is not None or deviation is not None) or None,
            nominal,
            deviation,
        )

    stabilized, nominal, deviation = get_tuple()
    if value and stabilized is None and nominal is None and deviation is None:
        # special EPN null case, where the null value is 'deg C +/- deg C'
        if (
            value.lower().replace(" ", "").replace("(", "").replace(")", "")
            == "degc+/-degc"
        ):
            return _Ignored("Looks like a placeholder."), None, None

        if "yes" in value.lower() or "indoors" in value.lower():
            return _Warning(value=True, msg="Interpreted as 'stabilized'"), None, None
        if value.startswith("("):
            return _Ignored("Looks like a placeholder."), None, None
        raise ValueError(
            f'Unable to parse "{value}" into a temperature stabilization. '
            f"format: deg C +/- deg C"
        )
    return stabilized, nominal, deviation


def effective_date(value: str, part: int, label: str):
    try:
        dt_str = ""
        if value.strip():
            sep = "/" if "/" in value else " - "
            splt = value.split(sep)
            if len(splt) > part:
                dt_str = splt[part]
                if dt_str.strip():
                    ret = to_date(dt_str.strip())
                    if isinstance(ret, _Ignored):
                        start = value.index(dt_str)
                        end = start + len(dt_str)
                        ret.columns = (start, end)
                    return ret
        return None
    except ValueError as ve:
        if dt_str.upper() in DATE_PLACEHOLDERS:
            return None
        raise ValueError(
            f"Unable to parse {value} into an expected {label} date. Expected "
            f"format: CCYY-MM-DD/CCYY-MM-DD"
        ) from ve


effective_start = partial(effective_date, part=0, label="start")
effective_end = partial(effective_date, part=1, label="end")


def no_sat_warning(line_no, parser, satellites):
    if not satellites:
        good_sats = "  \n".join([sat.name for sat in SatelliteSystem.objects.all()])
        return [
            Warn(
                line_no,
                parser,
                f"Expected constellation list delineated by '+' "
                f"(e.g. GPS+GLO). Must be one of \n{good_sats}",
            )
        ]
    return []


class SiteLogBinder(BaseBinder):
    EFFECTIVE_DATES = [
        (
            "Effective Dates",
            [("effective_start", effective_start), ("effective_end", effective_end)],
        ),
    ]

    METEROLOGICAL_TRANSLATION = [
        ("Manufacturer", ("manufacturer", to_str)),
        ("Serial Number", ("serial_number", to_str)),
        (
            "Height Diff to Ant",
            (
                "height_diff",
                partial(to_float, units=METERS, prefixes=ACCURACY_PREFIXES),
            ),
        ),
        ("Calibration date", ("calibration", to_date)),
        *EFFECTIVE_DATES,
        ("Notes", ("notes", to_str)),
    ]

    ONGOING_CONDITIONS = [
        *EFFECTIVE_DATES,
        ("Additional Information", ("additional_information", to_str)),
    ]

    AGENCY_POC = [
        ("Agency", ("agency", to_str)),
        ("Preferred Abbreviation", ("preferred_abbreviation", to_str)),
        ("Mailing Address", ("mailing_address", to_str)),
        ("Primary Contact::Contact Name", ("primary_name", to_str)),
        ("Primary Contact::Telephone (primary)", ("primary_phone1", to_str)),
        ("Primary Contact::Telephone (secondary)", ("primary_phone2", to_str)),
        ("Primary Contact::Fax", ("primary_fax", to_str)),
        ("Primary Contact::E-mail", ("primary_email", to_str)),
        ("Secondary Contact::Contact Name", ("secondary_name", to_str)),
        ("Secondary Contact::Telephone (primary)", ("secondary_phone1", to_str)),
        ("Secondary Contact::Telephone (secondary)", ("secondary_phone2", to_str)),
        ("Secondary Contact::Fax", ("secondary_fax", to_str)),
        ("Secondary Contact::E-mail", ("secondary_email", to_str)),
        ("Additional Information", ("additional_information", to_str)),
    ]

    # the translation table maps binding functions and names to normalized
    # parameter names. Multiple normalized parameter names can be bound to the
    # same binding name and are to allow slight permissible variations in
    # site log parameter names. In all cases - the "canonical" name for each
    # parameter should be listed *last* in the list.

    TRANSLATION_TABLE: Dict[
        Union[int, Tuple[int, int]],
        Dict[
            str,
            Union[
                Tuple[str, Callable],
                List[Tuple[str, Callable]],
                Tuple[
                    str, Callable, Callable[[int, SiteLogParser, Any], List[Finding]]
                ],
                List[
                    Tuple[
                        str,
                        Callable,
                        Callable[[int, SiteLogParser, Any], List[Finding]],
                    ]
                ],
                Tuple[Tuple[Tuple[str, ...], str, Callable]],
            ],
        ],
    ] = {
        0: {
            reg(log_name, 0, bindings): bindings
            for log_name, bindings in [
                ("Prepared By", ("prepared_by", to_str)),
                ("Prepared by (full name)", ("prepared_by", to_str)),
                ("Date", ("date_prepared", to_date)),
                ("Date Prepared", ("date_prepared", to_date)),
                ("Report Type", ("report_type", to_str)),
                ("If Update", ("", ignored)),
                ("Previous Site Log", ("previous_log", ignored)),
                ("Modified/Added Sections", ("modified_section", to_str)),
            ]
        },
        1: {
            reg(log_name, 1, bindings): bindings
            for log_name, bindings in [
                ("Site Name", ("site_name", to_str)),
                ("4 char ID", ("nine_character_id", ignored)),
                ("Four Character ID", ("nine_character_id", ignored)),
                ("Nine Character ID", ("nine_character_id", ignored)),
                ("Monument Inscription", ("monument_inscription", to_str)),
                ("IERS DOMES Number", ("iers_domes_number", to_str)),
                ("CDP Number", ("cdp_number", to_str)),
                ("Date", ("date_installed", to_datetime)),
                ("Date Installed", ("date_installed", to_datetime)),
                ("Monument Description", ("monument_description", to_str)),
                (
                    "Height of the Monument (m)",
                    ("monument_height", partial(to_float, units=METERS)),
                ),
                (
                    "Height of the Monument",
                    ("monument_height", partial(to_float, units=METERS)),
                ),
                ("Monument Foundation", ("monument_foundation", to_str)),
                (
                    "Foundation Depth (m)",
                    ("foundation_depth", partial(to_float, units=METERS)),
                ),
                (
                    "Foundation Depth",
                    ("foundation_depth", partial(to_float, units=METERS)),
                ),
                ("Marker Description", ("marker_description", to_str)),
                ("Geologic Characteristic", ("geologic_characteristic", to_str)),
                ("Bedrock Type", ("bedrock_type", to_str)),
                ("Bedrock Condition", ("bedrock_condition", to_str)),
                (
                    "Fracture Spacing",
                    ("fracture_spacing", partial(to_enum, FractureSpacing)),
                ),
                ("Fault Zones Nearby", ("fault_zones", to_str)),
                ("Distance/activity", ("distance", to_str)),
                ("Additional Information", ("additional_information", to_str)),
            ]
        },
        2: {
            **{
                reg(log_name, 2, bindings): bindings
                for log_name, bindings in [
                    ("City", ("city", to_str)),
                    ("City or Town", ("city", to_str)),
                    ("State or Province", ("state", to_str)),
                    (
                        "Country",
                        ("country", partial(to_enum, ISOCountry, strict=False)),
                    ),
                    (
                        "Country or Region",
                        ("country", partial(to_enum, ISOCountry, strict=False)),
                    ),
                    ("Tectonic Plate", ("tectonic", partial(to_enum, TectonicPlates))),
                    ("Approximate Position", ("", ignored)),
                    ("X coordinate", ("x", to_float)),
                    ("Y coordinate", ("y", to_float)),
                    ("Z coordinate", ("z", to_float)),
                    ("Latitude", ("latitude", to_decimal_degrees)),
                    ("Longitude", ("longitude", to_decimal_degrees)),
                    ("Elevation", ("elevation", to_float)),
                    ("Latitude (deg)", ("latitude", to_decimal_degrees)),
                    ("Longitude (deg)", ("longitude", to_decimal_degrees)),
                    ("Elevation (m)", ("elevation", to_float)),
                    ("X coordinate (m)", ("x", to_float)),
                    ("Y coordinate (m)", ("y", to_float)),
                    ("Z coordinate (m)", ("z", to_float)),
                    ("Latitude (N is +)", ("latitude", to_decimal_degrees)),
                    ("Longitude (E is +)", ("longitude", to_decimal_degrees)),
                    ("Elevation (m,ellips.)", ("elevation", to_float)),
                    ("Additional Information", ("additional_information", to_str)),
                ]
            },
            "collations": (
                (("x", "y", "z"), "xyz", to_point),
                (("latitude", "longitude", "elevation"), "llh", to_point),
            ),
        },
        3: {
            reg(log_name, 3, bindings): bindings
            for log_name, bindings in [
                ("Type", ("receiver_type", to_receiver)),
                ("Receiver Type", ("receiver_type", to_receiver)),
                (
                    "Satellite System",
                    ("satellite_system", to_satellites, no_sat_warning),
                ),
                ("Serial Number", ("serial_number", to_str)),
                ("Firmware Version", ("firmware", to_str)),
                (
                    "Elevation Cutoff Setting",
                    ("elevation_cutoff", partial(to_float, units=["deg", "degrees"])),
                ),
                ("Date", ("installed", to_datetime)),
                ("Date Installed", ("installed", to_datetime)),
                ("Date Removed", ("removed", to_datetime)),
                (
                    "Temperature Stabiliz.",
                    [
                        ("temp_stabilized", lambda val: to_temp_stab(val)[0]),
                        ("temp_nominal", lambda val: to_temp_stab(val)[1]),
                        ("temp_deviation", lambda val: to_temp_stab(val)[2]),
                    ],
                ),
                ("Additional Information", ("additional_info", to_str)),
            ]
        },
        4: {
            **{
                reg(log_name, 4, bindings): bindings
                for log_name, bindings in [
                    ("Type", ("antenna_type", to_antenna)),
                    ("Antenna Type", ("antenna_type", to_antenna)),
                    ("Serial Number", ("serial_number", to_str)),
                    (
                        "Antenna Reference Point",
                        (
                            "reference_point",
                            partial(
                                to_enum, AntennaReferencePoint, ignored=["ARP", "n/a"]
                            ),
                        ),
                    ),
                    (
                        "Marker->ARP Up Ecc.",
                        ("marker_up", partial(to_float, units=METERS)),
                    ),
                    (
                        "Marker->ARP North Ecc",
                        ("marker_north", partial(to_float, units=METERS)),
                    ),
                    (
                        "Marker->ARP East Ecc",
                        ("marker_east", partial(to_float, units=METERS)),
                    ),
                    (
                        "Marker->ARP Up Ecc. (m)",
                        ("marker_up", partial(to_float, units=METERS)),
                    ),
                    (
                        "Marker->ARP North Ecc(m)",
                        ("marker_north", partial(to_float, units=METERS)),
                    ),
                    (
                        "Marker->ARP East Ecc(m)",
                        ("marker_east", partial(to_float, units=METERS)),
                    ),
                    # this legacy parameter was replaced by marker_une, but lots of older files
                    # have it so might as well parse it.
                    (
                        "Antenna Height",
                        ("antenna_height", partial(to_float, units=METERS)),
                    ),
                    (
                        "Antenna Height (m)",
                        ("antenna_height", partial(to_float, units=METERS)),
                    ),
                    ############################################################################
                    ("Alignment from True N", ("alignment", to_alignment)),
                    ("Degree Offset from North", ("alignment", to_alignment)),
                    ("Antenna Radome Type", ("radome_type", to_radome)),
                    ("Radome Serial Number", ("radome_serial_number", to_str)),
                    ("Antenna Cable Type", ("cable_type", to_str)),
                    (
                        "Antenna Cable Length",
                        (
                            "cable_length",
                            partial(to_float, units=METERS, prefixes=ACCURACY_PREFIXES),
                        ),
                    ),
                    ("Date Installed", ("installed", to_datetime)),
                    ("Date", ("installed", to_datetime)),
                    ("Date Removed", ("removed", to_datetime)),
                    ("Additional Information", ("additional_information", to_str)),
                ]
            },
            "collations": (
                (("marker_up", "marker_north", "marker_east"), "marker_une", to_point),
            ),
            "optional": {"antenna_height"},
        },
        5: {
            **{
                reg(log_name, 5, bindings): bindings
                for log_name, bindings in [
                    # older names
                    ("Monument Name", ("name", to_str)),
                    ("Site Ref CDP Number", ("cdp_number", to_str)),
                    ("Site Ref Domes Number", ("domes_number", to_str)),
                    ("Tied Marker Name", ("name", to_str)),
                    ("Tied Marker Usage", ("usage", to_str)),
                    ("Tied Marker CDP Number", ("cdp_number", to_str)),
                    ("Tied Marker DOMES Number", ("domes_number", to_str)),
                    ("dx", ("dx", partial(to_float, units=["m"]))),
                    ("dy", ("dy", partial(to_float, units=["m"]))),
                    ("dz", ("dz", partial(to_float, units=["m"]))),
                    ("dx (m)", ("dx", partial(to_float, units=["m"]))),
                    ("dy (m)", ("dy", partial(to_float, units=["m"]))),
                    ("dz (m)", ("dz", partial(to_float, units=["m"]))),
                    (
                        "Accuracy",
                        (
                            "accuracy",
                            partial(
                                to_float,
                                units=["mm"],
                                prefixes=ACCURACY_PREFIXES,
                                take_first=False,
                            ),
                        ),
                    ),
                    (
                        "Accuracy (mm)",
                        (
                            "accuracy",
                            partial(
                                to_float,
                                units=["mm"],
                                prefixes=ACCURACY_PREFIXES,
                                take_first=False,
                            ),
                        ),
                    ),
                    ("Survey method", ("survey_method", to_str)),
                    ("Date", ("measured", to_datetime)),
                    ("Date Measured", ("measured", to_datetime)),
                    ("Additional Information", ("additional_information", to_str)),
                ]
            },
            "collations": ((("dx", "dy", "dz"), "diff_xyz", to_point),),
        },
        6: {
            reg(log_name, 6, bindings): bindings
            for log_name, bindings in [
                (
                    "Standard Type",
                    ("standard_type", partial(to_enum, FrequencyStandardType)),
                ),
                (
                    "Input Frequency",
                    ("input_frequency", partial(to_float, units=["MHz"])),
                ),
                ("Frequency", ("input_frequency", partial(to_float, units=["MHz"]))),
                *EFFECTIVE_DATES,
                ("Notes", ("notes", to_str)),
            ]
        },
        7: {
            reg(log_name, 7, bindings): bindings
            for log_name, bindings in [
                ("Instrumentation Type", ("instrument_type", to_str)),
                ("Status", ("status", partial(to_enum, CollocationStatus))),
                *EFFECTIVE_DATES,
                ("Notes", ("notes", to_str)),
            ]
        },
        (8, 1): {
            reg(log_name, (8, 1), bindings): bindings
            for log_name, bindings in [
                (
                    "Accuracy",
                    (
                        "accuracy",
                        partial(
                            to_float,
                            units=["%", "rel h", "% rel h"],
                            prefixes=ACCURACY_PREFIXES,
                            take_first=False,
                        ),
                    ),
                ),
                ("Humidity Sensor Model", ("model", to_str)),
                ("Data Sampling Interval", ("sampling_interval", to_seconds)),
                (
                    "Accuracy (% rel h)",
                    (
                        "accuracy",
                        partial(
                            to_float,
                            units=["%", "rel h", "% rel h"],
                            prefixes=ACCURACY_PREFIXES,
                            take_first=False,
                        ),
                    ),
                ),
                ("Aspiration", ("aspiration", partial(to_enum, Aspiration))),
                *METEROLOGICAL_TRANSLATION,
            ]
        },
        (8, 2): {
            reg(log_name, (8, 2), bindings): bindings
            for log_name, bindings in [
                ("Pressure Sensor Model", ("model", to_str)),
                ("Data Sampling Interval", ("sampling_interval", to_seconds)),
                ("Accuracy", ("accuracy", to_pressure)),
                *METEROLOGICAL_TRANSLATION,
            ]
        },
        (8, 3): {
            reg(log_name, (8, 3), bindings): bindings
            for log_name, bindings in [
                ("Temp. Sensor Model", ("model", to_str)),
                ("Data Sampling Interval", ("sampling_interval", to_seconds)),
                (
                    "Accuracy",
                    (
                        "accuracy",
                        partial(
                            to_float,
                            units=["deg C", "C"],
                            prefixes=ACCURACY_PREFIXES,
                            take_first=False,
                        ),
                    ),
                ),
                ("Aspiration", ("aspiration", partial(to_enum, Aspiration))),
                *METEROLOGICAL_TRANSLATION,
            ]
        },
        (8, 4): {
            reg(log_name, (8, 4), bindings): bindings
            for log_name, bindings in [
                ("Water Vapor Radiometer", ("model", to_str)),
                (
                    "Distance to Antenna",
                    ("distance_to_antenna", partial(to_float, units=METERS)),
                ),
                *METEROLOGICAL_TRANSLATION,
            ]
        },
        (8, 5): {
            reg(log_name, (8, 5), bindings): bindings
            for log_name, bindings in [
                ("Other Instrumentation", ("instrumentation", to_str))
            ]
        },
        (9, 1): {
            reg(log_name, (9, 1), bindings): bindings
            for log_name, bindings in [
                *ONGOING_CONDITIONS,
                ("Radio Interferences", ("interferences", to_str)),
                ("Observed Degradations", ("degradations", to_str)),
            ]
        },
        (9, 2): {
            reg(log_name, (9, 2), bindings): bindings
            for log_name, bindings in [
                *ONGOING_CONDITIONS,
                ("Multipath Sources", ("sources", to_str)),
            ]
        },
        (9, 3): {
            reg(log_name, (9, 3), bindings): bindings
            for log_name, bindings in [
                *ONGOING_CONDITIONS,
                ("Signal Obstructions", ("obstructions", to_str)),
            ]
        },
        10: {
            reg(log_name, 10, bindings): bindings
            for log_name, bindings in [
                ("Date", EFFECTIVE_DATES[0][1]),
                ("Event", ("event", to_str)),
            ]
        },
        11: {
            reg(log_name, 11, bindings): bindings for log_name, bindings in AGENCY_POC
        },
        12: {
            reg(log_name, 12, bindings): bindings for log_name, bindings in AGENCY_POC
        },
        13: {
            reg(log_name, 13, bindings): bindings
            for log_name, bindings in [
                ("Primary Data Center", ("primary", to_str)),
                ("Secondary Data Center", ("secondary", to_str)),
                ("URL for More Information", ("more_info", concat_str)),
                ("Site Map", ("sitemap", to_str)),
                ("Site Diagram", ("site_diagram", to_str)),
                ("Horizon Mask", ("horizon_mask", to_str)),
                ("Monument Description", ("monument_description", to_str)),
                ("Site Pictures", ("site_picture", to_str)),
                ("Additional Information", ("additional_information", to_str)),
            ]
        },
    }

    MULTIPLE_ENTRIES = {
        3,
        4,
        5,
        6,
        7,
        (8, 1),
        (8, 2),
        (8, 3),
        (8, 4),
        (8, 5),
        (9, 1),
        (9, 2),
        (9, 3),
        10,
    }

    def __init__(self, parsed: SiteLogParser):
        super().__init__(parsed)
        for section in self.parsed.sections.values():
            if section.example:
                continue
            section_depth = sum(1 for item in section.index_tuple if item is not None)
            heading_depth = (
                1
                if not isinstance(section.heading_index, tuple)
                else len(section.heading_index)
            )
            is_header = (
                section.heading_index in self.MULTIPLE_ENTRIES
                and section_depth == heading_depth
            )
            if is_header and not section.contains_values:
                # skip empty headers
                continue
            if section.heading_index not in self.TRANSLATION_TABLE:
                for _ in range(section.line_no, section.line_end):
                    self.parsed.add_finding(
                        Warn(
                            section.line_no,
                            self.parsed,
                            f"Unexpected section {section.index_string}",
                            section=section,
                        )
                    )
            else:
                self.bind_section(
                    section=section,
                    translations=self.TRANSLATION_TABLE[section.heading_index],
                )

    def bind_section(
        self,
        section: ParsedSection,
        translations: Dict[
            str,
            Union[
                Tuple[str, Callable],
                List[Tuple[str, Callable]],
                Tuple[
                    str, Callable, Callable[[int, SiteLogParser, Any], List[Finding]]
                ],
                List[
                    Tuple[
                        str,
                        Callable,
                        Callable[[int, SiteLogParser, Any], List[Finding]],
                    ]
                ],
                Tuple[Tuple[Tuple[str, ...], str, Callable]],
            ],
        ],
    ) -> None:
        expected = set()
        binding_errors = set()
        ignored = set()
        optional = translations.get("optional", set())
        for _1, bindings in translations.items():
            if _1 in ["collations", "optional"]:
                continue
            for param in bindings if isinstance(bindings, list) else [bindings]:
                expected.add(param[0])

        for norm_name, parameter in section.parameters.items():
            translation = translations.get(norm_name, None)
            while not translation and "::" in norm_name:
                norm_name = [part for part in norm_name.split("::") if part.strip()][0]
                translation = translations.get(norm_name, None)

            if not translation:
                self.parsed.add_finding(
                    Warn(
                        parameter.line_no,
                        self.parsed,
                        f"Unrecognized parameter: {parameter.name}",
                        section=section,
                    )
                )
                continue

            for param in (
                translation if isinstance(translation, list) else [translation]
            ):
                value_check = param[2] if len(param) > 2 else lambda _1, _2, _3: []
                parse = param[1]
                param = param[0]
                try:
                    value = (
                        parse("")
                        if parameter.is_placeholder
                        else parse(parameter.value)
                    )
                    if isinstance(value, _Ignored):
                        cols = None
                        if cols := getattr(value, "columns", None):
                            val_start = self.lines[parameter.line_no].index(
                                parameter.value
                            )
                            cols = (cols[0] + val_start, cols[1] + val_start)
                        self.parsed.add_finding(
                            Ignored(
                                parameter.line_no,
                                self.parsed,
                                getattr(value, "msg", _("Parameter is ignored")),
                                section=section,
                                columns=cols,
                            )
                        )
                        ignored.add(param)
                        parameter.bind(param, None)
                    elif isinstance(value, _Warning):
                        self.parsed.add_finding(
                            Warn(
                                parameter.line_no,
                                self.parsed,
                                value.msg,
                                section=section,
                            )
                        )
                        parameter.bind(param, value.value)
                    else:
                        parameter.bind(param, value)
                        for finding in value_check(
                            parameter.line_no, self.parsed, value
                        ):
                            self.parsed.add_finding(finding)

                except Exception as err:
                    binding_errors.add(param)
                    for line_no in range(parameter.line_no, parameter.line_end + 1):
                        self.parsed.add_finding(
                            Error(line_no, self.parsed, str(err), section=section)
                        )

        # if any binding parameters were not found attach a listing
        # of them as an error to the relevant header line
        missing = [
            param
            for param in expected
            if param
            and not section.get_params(param)
            and param not in binding_errors
            and param not in ignored
            and param not in optional
        ]
        if missing and not self.parsed.findings.get(section.line_no):
            missing = "\n".join(
                {param_registry[section.heading_index][missing] for missing in missing}
            )
            self.parsed.add_finding(
                Warn(
                    section.line_no,
                    self.parsed,
                    f"Missing parameters:\n{missing}",
                    section=section,
                )
            )

        # run through collations and adjust bindings
        if section.binding:
            for collation in translations.get("collations", []):
                assert len(collation) == 3
                if any(param in section.binding for param in collation[0]):
                    try:
                        section.collate(
                            collation[0],
                            collation[1],
                            collation[2](
                                *[
                                    section.binding.get(param, None)
                                    for param in collation[0]
                                ]
                            ),
                        )
                    except Exception:
                        # todo
                        pass
