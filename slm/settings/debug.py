
from django.core.exceptions import ImproperlyConfigured

if DJANGO_DEBUG_TOOLBAR:
    try:
        import debug_toolbar
    except ImportError:
        raise ImproperlyConfigured(
            'DJANGO_DEBUG_TOOLBAR is True, but django-debug-toolbar is not'
            'installed.'
        )

    # list any middlewares that might be encountered on the stack that must
    # have higher precedence than debug middelware
    if 'debug_toolbar.middleware.DebugToolbarMiddleware' not in MIDDLEWARE:
        must_come_after = ['django.middleware.gzip.GZipMiddleware']
        position = None
        for middleware in must_come_after:
            try:
                middleware_idx = MIDDLEWARE.index(middleware)
                if position is None or middleware_idx > position:
                    position = middleware_idx
            except ValueError:
                pass
        MIDDLEWARE.insert(
            position or 0,
            'debug_toolbar.middleware.DebugToolbarMiddleware'
        )

    if 'debug_toolbar' not in INSTALLED_APPS:
        INSTALLED_APPS.append('debug_toolbar')

    import socket  # only if you haven't already imported this
    try:
        _, _, ips = socket.gethostbyname_ex(socket.gethostname())
    except OSError:
        _, _, ips = socket.gethostbyname_ex('localhost')

    set_default(
        'INTERNAL_IPS',
        []
    )
    INTERNAL_IPS.extend(
        [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]
    )

    set_default(
        'DEBUG_TOOLBAR_CONFIG',
        {'SHOW_TOOLBAR_CALLBACK': lambda _: True}
    )
