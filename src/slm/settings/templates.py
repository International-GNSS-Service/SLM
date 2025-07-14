from jinja2 import select_autoescape

from slm.settings import set_default

set_default(
    "TEMPLATES",
    [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "slm.context.globals",
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
                "environment": "slm.templatetags.jinja2.compat",
            },
        },
    ],
)
