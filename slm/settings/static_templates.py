def get_enum_context():
    # this needs to be wrapped in a function call because these enums use the
    # translation infrastructure which cannot be invoked before settings have
    # been fully realized.
    from slm.defines import (
        LogEntryType,
        SiteLogStatus,
        AlertLevel
    )
    return {
        'LogEntryType': LogEntryType,
        'SiteLogStatus': SiteLogStatus,
        'AlertLevel': AlertLevel
    }


STATIC_TEMPLATES = {
    'templates': {
        'slm/js/urls.js': {
            'context': {
                'exclude': ['admin']
            }
        },
        'slm/js/enums.js': {
            'context': get_enum_context
        }
    }
}
