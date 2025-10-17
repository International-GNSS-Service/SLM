"""
This file contains the default validation configuration configuration
for site log fields. Amend or override SLM_DATA_VALIDATORS to use
different routines.

The format of SLM_DATA_VALIDATORS is
{
    <app_label>.<ModelCalss>: {
        '<field_name>': [Validator1(), Validator2(), ...]
    }
}
"""

from slm.settings import set_default
from slm.validators import (
    ActiveEquipmentValidator,
    ARPValidator,
    EnumValidator,
    FieldRequired,
    NonEmptyValidator,
    PositionsMatchValidator,
    TimeRangeBookendValidator,
    TimeRangeValidator,
    VerifiedEquipmentValidator,
)

# toggling this off will prevent any validation configured to block edit saves
# from doing so - instead flags will be issued.
set_default("SLM_VALIDATION_BYPASS_BLOCK", False)

# do not allow a log to be published without these sections
set_default(
    "SLM_REQUIRED_SECTIONS_TO_PUBLISH",
    [
        "siteform",
        "siteidentification",
        "sitelocation",
        "sitereceiver",
        "siteantenna",
        # 'sitesurveyedlocalties',
        # 'sitefrequencystandard',
        # 'sitecollocation',
        # 'sitehumiditysensor',
        # 'sitepressuresensor',
        # 'sitetemperaturesensor',
        # 'sitewatervaporradiometer',
        # 'siteotherinstrumentation',
        # 'siteradiointerferences',
        # 'sitemultipathsources',
        # 'sitesignalobstructions',
        # 'sitelocalepisodiceffects',
        # "siteoperationalcontact",
        # 'siteresponsibleagency',
        # 'sitemoreinformation'
    ],
)

# the model field to validator map
set_default(
    "SLM_DATA_VALIDATORS",
    {
        "slm.SiteIdentification": {
            "site_name": [FieldRequired()],
            "fracture_spacing": [FieldRequired(desired=True), EnumValidator()],
            "iers_domes_number": [FieldRequired()],
            "date_installed": [FieldRequired()],
        },
        "slm.SiteLocation": {
            "city": [FieldRequired()],
            "country": [FieldRequired(), EnumValidator()],
            "tectonic": [EnumValidator()],
            "xyz": [FieldRequired(), PositionsMatchValidator()],
            "llh": [FieldRequired(), PositionsMatchValidator()],
        },
        "slm.SiteReceiver": {
            "receiver_type": [VerifiedEquipmentValidator(), ActiveEquipmentValidator()],
            "satellite_system": [NonEmptyValidator()],
            "serial_number": [FieldRequired()],
            "firmware": [FieldRequired()],
            "installed": [FieldRequired(), TimeRangeValidator(end_field="removed")],
            "removed": [
                TimeRangeValidator(start_field="installed"),
                TimeRangeBookendValidator(),
            ],
        },
        "slm.SiteAntenna": {
            "antenna_type": [VerifiedEquipmentValidator(), ActiveEquipmentValidator()],
            "radome_type": [VerifiedEquipmentValidator(), ActiveEquipmentValidator()],
            "serial_number": [FieldRequired()],
            "reference_point": [FieldRequired(), ARPValidator(), EnumValidator()],
            "installed": [FieldRequired(), TimeRangeValidator(end_field="removed")],
            "removed": [
                TimeRangeValidator(start_field="installed"),
                TimeRangeBookendValidator(),
            ],
            "marker_une": [FieldRequired(allow_legacy_nulls=True)],
            "alignment": [FieldRequired(allow_legacy_nulls=True, desired=True)],
        },
        "slm.SiteSurveyedLocalTies": {
            "name": [FieldRequired()],
            "measured": [FieldRequired(allow_legacy_nulls=True)],
            "diff_xyz": [FieldRequired(allow_legacy_nulls=True)],
        },
        "slm.SiteFrequencyStandard": {
            "standard_type": [FieldRequired(), EnumValidator()],
            "effective_start": [
                FieldRequired(),
                TimeRangeValidator(end_field="effective_end"),
            ],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteCollocation": {
            "instrument_type": [FieldRequired()],
            "status": [FieldRequired(allow_legacy_nulls=True), EnumValidator()],
            "effective_start": [
                FieldRequired(),
                TimeRangeValidator(end_field="effective_end"),
            ],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteHumiditySensor": {
            "model": [FieldRequired()],
            "manufacturer": [FieldRequired()],
            "height_diff": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [TimeRangeValidator(end_field="effective_end")],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
            "aspiration": [FieldRequired(allow_legacy_nulls=True), EnumValidator()],
        },
        "slm.SitePressureSensor": {
            "model": [FieldRequired()],
            "manufacturer": [FieldRequired()],
            "height_diff": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [TimeRangeValidator(end_field="effective_end")],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteTemperatureSensor": {
            "model": [FieldRequired()],
            "manufacturer": [FieldRequired()],
            "height_diff": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [TimeRangeValidator(end_field="effective_end")],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
            "aspiration": [FieldRequired(allow_legacy_nulls=True), EnumValidator()],
        },
        "slm.SiteWaterVaporRadiometer": {
            "model": [FieldRequired()],
            "manufacturer": [FieldRequired()],
            "distance_to_antenna": [FieldRequired(allow_legacy_nulls=True)],
            "height_diff": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [TimeRangeValidator(end_field="effective_end")],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteOtherInstrumentation": {"instrumentation": [FieldRequired()]},
        "slm.SiteRadioInterferences": {
            "interferences": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [
                FieldRequired(),
                TimeRangeValidator(end_field="effective_end"),
            ],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteMultiPathSources": {
            "sources": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [
                FieldRequired(),
                TimeRangeValidator(end_field="effective_end"),
            ],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteSignalObstructions": {
            "obstructions": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [
                FieldRequired(),
                TimeRangeValidator(end_field="effective_end"),
            ],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteLocalEpisodicEffects": {
            "event": [FieldRequired(allow_legacy_nulls=True)],
            "effective_start": [
                FieldRequired(),
                TimeRangeValidator(end_field="effective_end"),
            ],
            "effective_end": [TimeRangeValidator(start_field="effective_start")],
        },
        "slm.SiteOperationalContact": {
            "agency": [FieldRequired()],
            "preferred_abbreviation": [FieldRequired()],
            "primary_name": [FieldRequired()],
            "primary_phone1": [FieldRequired(desired=True)],
            "primary_email": [FieldRequired(allow_legacy_nulls=True)],
        },
        "slm.SiteMoreInformation": {
            "primary": [FieldRequired()],
            "secondary": [FieldRequired()],
        },
    },
)
