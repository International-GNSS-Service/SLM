# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/
from slm.settings import env as settings_environment
from slm.settings import get_setting, set_default

env = settings_environment()

LANGUAGE_CODE = env("LANGUAGE_CODE", default=get_setting("LANGUAGE_CODE", "en-us"))

# ALL TIMES IN THE DB SHOULD BE STORED IN UTC - The web interface can then
# reliably translate this into browser local time
set_default("TIME_ZONE", "UTC")
set_default("USE_I18N", not bool(LANGUAGE_CODE.startswith("en")))
set_default("USE_TZ", True)
