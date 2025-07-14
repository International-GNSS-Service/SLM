from importlib.util import find_spec

from django.core.exceptions import ImproperlyConfigured

from slm.settings import get_setting, set_default

if get_setting("SLM_DEBUG_TOOLBAR", False):
    if not find_spec("debug_toolbar"):
        raise ImproperlyConfigured(
            "SLM_DEBUG_TOOLBAR is True, but django-debug-toolbar is notinstalled."
        )

    # list any middlewares that might be encountered on the stack that must
    # have higher precedence than debug middelware

    MIDDLEWARE = get_setting("MIDDLEWARE", [])
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:
        must_come_after = ["django.middleware.gzip.GZipMiddleware"]
        position = None
        for middleware in must_come_after:
            try:
                middleware_idx = MIDDLEWARE.index(middleware)
                if position is None or middleware_idx > position:
                    position = middleware_idx
            except ValueError:
                pass
        MIDDLEWARE.insert(
            position or 0, "debug_toolbar.middleware.DebugToolbarMiddleware"
        )

    INSTALLED_APPS = get_setting("INSTALLED_APPS", [])
    if "debug_toolbar" not in INSTALLED_APPS:
        INSTALLED_APPS.append("debug_toolbar")

    import socket  # only if you haven't already imported this

    try:
        _, _, ips = socket.gethostbyname_ex(socket.gethostname())
    except OSError:
        _, _, ips = socket.gethostbyname_ex("localhost")

    INTERNAL_IPS = get_setting("INTERNAL_IPS", [])
    INTERNAL_IPS.extend(
        [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]
    )

    set_default("DEBUG_TOOLBAR_CONFIG", {"SHOW_TOOLBAR_CALLBACK": lambda _: True})
