from slm.settings import get_setting, set_default


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
        "enums": [
            LogEntryType,
            SiteLogStatus,
            AlertLevel,
            SiteFileUploadStatus,
            SiteLogFormat,
            SLMFileType,
        ]
    }


def get_defines_context():
    from slm.defines import AlertLevel, SiteLogStatus

    return {"AlertLevel": AlertLevel, "SiteLogStatus": SiteLogStatus}


def get_icon_context():
    from django.conf import settings

    from slm.templatetags.slm import file_icon

    return {
        "ICON_MAP": getattr(settings, "SLM_FILE_ICONS", {}),
        "DEFAULT_ICON": file_icon(""),
    }


set_default(
    "STATIC_TEMPLATES",
    {
        "templates": [
            ("slm/js/urls.js", {"dest": get_setting("STATIC_ROOT") / "urls.js"}),
            ("slm/js/enums.js", {"context": get_enum_context}),
            ("slm/js/fileIcons.js", {"context": get_icon_context}),
            ("slm/css/defines.css", {"context": get_defines_context}),
        ]
    },
)
