from split_settings.tools import include, optional
from slm.settings import resource, set_default, get_setting

set_default("SLM_ORG_NAME", "{{ organization }}")
include(resource("slm.settings", "root.py"))
include(optional('./validation.py'))

INSTALLED_APPS = [
    "{{ extension_app }}",
    {% if not include_map %}# {% endif %}"slm.map",
    *get_setting("INSTALLED_APPS", [])
]


ROOT_URLCONF = "sites.{{ site }}.urls"
