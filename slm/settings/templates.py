from jinja2 import Environment, Undefined, select_autoescape

from slm.templatetags import slm


def site_log_rendering(**options):
    env = Environment(**{**options, "undefined": Undefined})
    env.filters.update(slm.register.filters)
    return env


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": ["slm.templatetags.slm"],
        },
    },
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "APP_DIRS": True,
        "OPTIONS": {
            "autoescape": select_autoescape(
                disabled_extensions=("log",),
                default_for_string=True,
                default=True,
            ),
            "environment": "slm.settings.templates.site_log_rendering",
        },
    },
]
