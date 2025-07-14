from slm.settings import env as settings_environment
from slm.settings import (
    get_setting,
    slm_path_mk_dirs_must_exist,
    slm_path_must_exist,
    split_email_str,
)

env = settings_environment()

_email_config = env.email_url(
    "SLM_EMAIL_SERVER", default=get_setting("SLM_EMAIL_SERVER", "smtp://localhost:25")
)
if EMAIL_FILE_PATH := _email_config.pop("EMAIL_FILE_PATH", None):
    EMAIL_FILE_PATH = slm_path_mk_dirs_must_exist(EMAIL_FILE_PATH)

if not EMAIL_FILE_PATH:
    del EMAIL_FILE_PATH

vars().update(_email_config)

SERVER_EMAIL = env("SERVER_EMAIL", default=get_setting("SERVER_EMAIL", None))
if SERVER_EMAIL is None:
    domain = (
        get_setting("SLM_SITE_NAME", None)
        or get_setting("ALLOWED_HOSTS", ["localhost"])[0]
    )
    SERVER_EMAIL = f"noreply@{domain}"

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=SERVER_EMAIL)


EMAIL_SSL_CERTFILE = env(
    "EMAIL_SSL_CERTFILE",
    slm_path_must_exist,
    default=get_setting("EMAIL_SSL_CERTFILE", None),
)
EMAIL_SSL_KEYFILE = env(
    "EMAIL_SSL_KEYFILE",
    slm_path_must_exist,
    default=get_setting("EMAIL_SSL_KEYFILE", None),
)


# these emails will receive email reports when 500 HTTP messages are returned
# TODO - on Django 6+ change this from email_str -> tuple to tuple -> email str
ADMINS = [
    split_email_str(email) if isinstance(email, str) else email
    for email in env.list("ADMINS", default=get_setting("ADMINS", []))
]
