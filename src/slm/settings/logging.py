import os
from logging import Filter

from slm.settings import env as settings_environment
from slm.settings import get_setting, is_defined, slm_path_mk_dirs_must_exist

env = settings_environment()

DEBUG = get_setting("DEBUG", False)
SLM_LOG_LEVEL = env(
    "SLM_LOG_LEVEL", default=get_setting("SLM_LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
)
SLM_LOG_DIR = env(
    "SLM_LOG_DIR",
    slm_path_mk_dirs_must_exist,
    default=get_setting("SLM_LOG_DIR", get_setting("BASE_DIR") / "logs"),
)
SLM_MANAGEMENT_MODE = get_setting("SLM_MANAGEMENT_MODE", False)


class SquelchStackTraces(Filter):
    def filter(self, record):
        record.exc_info = None
        return super().filter(record)


if not is_defined("LOGGING"):
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "file": {
                "level": SLM_LOG_LEVEL,  # set in deployment routine
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "verbose"
                if DEBUG
                else "simple",  # set in deployment routine
                "filename": SLM_LOG_DIR
                / f"{get_setting('SLM_SITE_NAME', '').lower()}{'_manage' if SLM_MANAGEMENT_MODE else ''}.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 14,
            },
            "mail_admins": {
                "level": "ERROR",
                "class": "django.utils.log.AdminEmailHandler",
                "include_html": True,
            },
        },
        "formatters": {
            "verbose": {
                "format": "%(levelname)s %(process)d  %(asctime)s %(name)s %(process)d %(thread)d %(message)s"
            },
            "simple": {
                "format": "%(levelname)s %(process)d  %(asctime)s %(name)s %(message)s"
            },
            "management": {"format": "%(message)s"},
        },
        "filters": {
            "squelch_traces": {
                "()": SquelchStackTraces,
            },
        },
        "loggers": {
            "django.request": {
                "handlers": ["mail_admins"],
                "level": "ERROR",
                "propagate": True,
            },
            "django": {
                "handlers": ["file"],
                "level": SLM_LOG_LEVEL,
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": ["file"],
                "level": "INFO",  # super noisy
                "propagate": False,
            },
            "django.template": {
                "handlers": ["file"],
                "filters": ["squelch_traces"],
                "level": "INFO",
                "propagate": False,
            },
            "django.utils.autoreload": {
                "handlers": ["file"],
                "level": "WARNING",  # this logger got really noisy in django 2.2
                "propagate": False,
            },
            "django_auth_ldap": {"level": SLM_LOG_LEVEL, "propagate": True},
        },
        "root": {
            "handlers": ["file", "mail_admins"],
            "level": SLM_LOG_LEVEL,  # set in deployment routine
        },
    }

    if DEBUG and not SLM_MANAGEMENT_MODE:
        LOGGING["loggers"]["core.middleware.RequestLogger"] = {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": False,
        }

    if SLM_MANAGEMENT_MODE:
        LOGGING.setdefault("handlers", {})["console"] = {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "management",
        }

        if "root" in LOGGING:
            if "console" not in LOGGING["root"]["handlers"]:
                LOGGING["root"]["handlers"].append("console")

        for name, config in LOGGING.get("loggers", {}).items():
            if "handlers" in config and "console" not in config["handlers"]:
                config["handlers"].append("console")

    # create logging dirs if necessary
    for name, handler_spec in LOGGING["handlers"].items():
        filename = handler_spec.get("filename", None)
        if filename:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
