from slm.settings import get_setting
{% if use_igs_validation %}

SLM_DATA_VALIDATORS = get_setting("SLM_DATA_VALIDATORS")

# You have elected to use the IGS site log validators, you may make modifications
# to the configured validators by making changes to SLM_DATA_VALIDATORS above.

{% else %}
# You selected to not use the IGS sitelog field validators by default, you may
# define your own validation configuration here. See slm.settings.validation
# module (https://github.com/International-GNSS-Service/SLM/blob/master/slm/settings/validation.py)
# for what the default settings are and documentation here (TODO) for the SLM's pluggable
# validation system.
SLM_DATA_VALIDATORS = get_setting("SLM_DATA_VALIDATORS", {})

SLM_REQUIRED_SECTIONS_TO_PUBLISH = [
    "siteform",
    "siteidentification",
    "sitelocation",
    "sitereceiver",
    "siteantenna",
    "siteoperationalcontact"
]

SLM_VALIDATION_BYPASS_BLOCK = False
{% endif %}

# You may delete this file if you do not need to make any modifications
