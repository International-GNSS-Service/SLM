from jinja2 import Environment, Undefined

from slm.templatetags import slm


def compat(**options):
    # autoescape is configured in the TEMPLATES OPTIONS (see settings/templates.py)
    env = Environment(**{**options, "undefined": Undefined})  # nosec B701
    env.filters.update(slm.register.filters)
    return env
