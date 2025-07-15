from split_settings.tools import include, optional
from slm.settings import resource, set_default, get_setting

set_default("SLM_ORG_NAME", "{{ organization }}")

SLM_DATABASE = "{{ database }}"

{% if not include_map %}
SLM_ADMIN_MAP = False
{% endif %}

{% if not use_igs_validation %}
SLM_IGS_VALIDATION = False
{% endif %}

include(resource("slm.settings", "root.py"))
include(optional('./validation.py'))


INSTALLED_APPS = [
    "{{ extension_app }}",
    *get_setting("INSTALLED_APPS", [])
]


ROOT_URLCONF = "sites.{{ site }}.urls"
