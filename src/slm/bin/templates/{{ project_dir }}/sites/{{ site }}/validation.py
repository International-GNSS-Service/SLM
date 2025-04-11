{% if not use_igs_validation %}
# You selected to not use the IGS sitelog field validators by default, you may
# define your own validation configuration here. See slm.settings.validation
# module (https://github.com/International-GNSS-Service/SLM/blob/master/slm/settings/validation.py)
# for what the default settings are and documentation here (TODO) for the SLM's pluggable
# validation system.
SLM_REQUIRED_SECTIONS_TO_PUBLISH = []
SLM_DATA_VALIDATORS = {}

# You may delete this file to always use IGS's default validation routines
{% endif %}
