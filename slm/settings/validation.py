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
from slm.validators import (
    EnumValidator,
    TimeRangeValidator,
    FieldRequiredToPublish,
    ARPValidator,
    NonEmptyValidator,
    VerifiedEquipmentValidator
)

# toggling this off will prevent any validation configured to block edit saves
# from doing so - instead flags will be issued.
SLM_VALIDATION_BYPASS_BLOCK = False

# the model field to validator map
SLM_DATA_VALIDATORS = {
    'slm.SiteIdentification': {
        'fracture_spacing': [EnumValidator()],
    },
    'slm.SiteLocation': {
        'country': [EnumValidator()],
        'tectonic': [EnumValidator()]
    },
    'slm.SiteReceiver': {
        'receiver_type': [
            VerifiedEquipmentValidator()
        ],
        'satellite_system': [
            NonEmptyValidator()
        ],
        'installed': [
            FieldRequiredToPublish(),
            TimeRangeValidator(end_field='removed')
        ],
        'removed': [
            TimeRangeValidator(start_field='installed')
        ]
    },
    'slm.SiteAntenna': {
        'antenna_type': [
            VerifiedEquipmentValidator()
        ],
        'radome_type': [
            VerifiedEquipmentValidator()
        ],
        'reference_point': [ARPValidator(), EnumValidator()],
        'installed': [
            FieldRequiredToPublish(),
            TimeRangeValidator(end_field='removed')
        ],
        'removed': [TimeRangeValidator(start_field='installed')]
    },
    'slm.SiteFrequencyStandard': {
        'standard_type': [EnumValidator()],
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')],
    },
    'slm.SiteCollocation': {
        'status': [EnumValidator()],
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')]
    },
    'slm.SiteHumiditySensor': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')],
        'aspiration': [EnumValidator()]
    },
    'slm.SitePressureSensor': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')]
    },
    'slm.SiteTemperatureSensor': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')],
        'aspiration': [EnumValidator()]
    },
    'slm.SiteWaterVaporRadiometer': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')]
    },
    'slm.SiteRadioInterferences': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')]
    },
    'slm.SiteMultiPathSources': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')]
    },
    'slm.SiteSignalObstructions': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')]
    },
    'slm.SiteLocalEpisodicEffects': {
        'effective_start': [TimeRangeValidator(end_field='effective_end')],
        'effective_end': [TimeRangeValidator(start_field='effective_start')]
    }
}
