def get_enum_context():
    # this needs to be wrapped in a function call because these enums use the
    # translation infrastructure which cannot be invoked before settings have
    # been fully realized.
    from slm.defines import (
        AlertLevel,
        LogEntryType,
        SiteFileUploadStatus,
        SiteLogFormat,
        SiteLogStatus,
        SLMFileType,
    )
    return {
        'LogEntryType': LogEntryType,
        'SiteLogStatus': SiteLogStatus,
        'AlertLevel': AlertLevel,
        'SiteFileUploadStatus': SiteFileUploadStatus,
        'SiteLogFormat': SiteLogFormat,
        'SLMFileType': SLMFileType
    }


def get_icon_context():
    from django.conf import settings
    from slm.templatetags.slm import file_icon
    return {
        'ICON_MAP': getattr(settings, 'SLM_FILE_ICONS', {}),
        'DEFAULT_ICON': file_icon('')
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
        },
        'slm/js/fileIcons.js': {
            'context': get_icon_context
        }
    }
}
