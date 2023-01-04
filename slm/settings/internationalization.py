# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = 'en'

# ALL TIMES IN THE DB SHOULD BE STORED IN UTC - The web interface can then
# reliably translate this into browser local time
TIME_ZONE = 'UTC'

USE_I18N = False

USE_L10N = True

# TODO change to True with port in
USE_TZ = True
