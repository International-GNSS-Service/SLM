from jinja2 import Environment
from slm.templatetags import slm


def environment(**options):
    env = Environment(**options)
    env.filters.update(slm.register.filters)
    return env
