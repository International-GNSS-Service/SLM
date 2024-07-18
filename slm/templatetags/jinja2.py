from jinja2 import Environment, Undefined

from slm.templatetags import slm


def compat(**options):
    env = Environment(**{**options, "undefined": Undefined})
    env.filters.update(slm.register.filters)
    return env
