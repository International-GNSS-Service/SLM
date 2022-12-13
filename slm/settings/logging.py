import os

from slm.settings import set_default

DEFAULT_LOG_LEVEL = 'INFO'
if DEBUG:
    DEFAULT_LOG_LEVEL = 'DEBUG'

set_default('LOG_DIR', BASE_DIR / 'logs')


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': DEFAULT_LOG_LEVEL,  # set in deployment routine
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'verbose' if DEBUG else 'simple',  # set in deployment routine
            'filename': LOG_DIR / f'{SITE_NAME.lower()}{"_manage" if MANAGEMENT_MODE else ""}.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 14
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(process)d  %(asctime)s %(name)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(process)d  %(asctime)s %(name)s %(message)s'
        },
        'management': {
            'format': '%(message)s'
        }
    },
    'filters': {
        'squelch_traces': {
            '()': 'slm.utils.SquelchStackTraces',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': DEFAULT_LOG_LEVEL,
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'INFO',  # super noisy
            'propagate': False,
        },
        'django.template': {
            'handlers': ['file'],
            'filters': ['squelch_traces'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.utils.autoreload': {
            'handlers': ['file'],
            'level': 'WARNING',  # this logger got really noisy in django 2.2
            'propagate': False
        },
        'django_auth_ldap': {
            'level': DEFAULT_LOG_LEVEL,
            'propagate': True
        }
    },
    'root': {
        'handlers': ['file', 'mail_admins'],
        'level': DEFAULT_LOG_LEVEL,  # set in deployment routine
    },
}

if DEBUG and not MANAGEMENT_MODE:
    LOGGING['loggers']['core.middleware.RequestLogger'] = {
        'handlers': ['file'],
        'level': 'DEBUG',
        'propagate': False,
    }

if MANAGEMENT_MODE:
    LOGGING.setdefault('handlers', {})['console'] = {
        'level': 'INFO',
        'class': 'logging.StreamHandler',
        'formatter': 'management',
    }

    if 'root' in LOGGING:
        if 'console' not in LOGGING['root']['handlers']:
            LOGGING['root']['handlers'].append('console')

    for name, config in LOGGING.get('loggers', {}).items():
        if 'handlers' in config and 'console' not in config['handlers']:
            config['handlers'].append('console')

# create logging dirs if necessary
for name, handler_spec in LOGGING['handlers'].items():
    filename = handler_spec.get('filename', None)
    if filename:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
