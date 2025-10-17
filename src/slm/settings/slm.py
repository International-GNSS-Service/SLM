"""
SLM Specific Configuration parameters go here. what
"""

from django.utils.translation import gettext_lazy as _

from slm.defines import (
    AlertLevel,
    CoordinateMode,
    GeodesyMLVersion,
    SiteFileUploadStatus,
    SiteLogFormat,
    SiteLogStatus,
)
from slm.settings import env as settings_environment
from slm.settings import get_setting, set_default

env = settings_environment()

DEBUG = get_setting("DEBUG")

set_default(
    "SLM_ALERT_COLORS",
    {
        AlertLevel.NOTICE: "#12CAF0",
        AlertLevel.WARNING: "#E3AA00",
        AlertLevel.ERROR: "#DD3444",
    },
)

set_default(
    "SLM_STATUS_COLORS",
    {
        SiteLogStatus.FORMER: "#3D4543",
        SiteLogStatus.SUSPENDED: "#E0041A",
        SiteLogStatus.PROPOSED: "#913D88",
        SiteLogStatus.UPDATED: "#0079AD",
        SiteLogStatus.PUBLISHED: "#0D820D",
        SiteLogStatus.EMPTY: "#D3D3D3",
    },
)

set_default(
    "SLM_FILE_COLORS",
    {
        SiteFileUploadStatus.UNPUBLISHED: "#0079AD",
        SiteFileUploadStatus.PUBLISHED: "#0D820D",
        SiteFileUploadStatus.INVALID: "#8b0000",
        SiteFileUploadStatus.WARNINGS: "#E3AA00",
        SiteFileUploadStatus.VALID: "#0D820D",
    },
)

# if True, for subsections and missing sections, placeholder structures will
# be added to the logs
SLM_LEGACY_PLACEHOLDERS = env(
    "SLM_LEGACY_PLACEHOLDERS", default=get_setting("SLM_LEGACY_PLACEHOLDERS", True)
)

# the maximum file upload size in Mega Bytes
SLM_MAX_UPLOAD_SIZE_MB = env(
    "SLM_MAX_UPLOAD_SIZE_MB", default=get_setting("SLM_MAX_UPLOAD_SIZE_MB", 100)
)

# a map of file icons (css) from mimetype subtypes
set_default(
    "SLM_FILE_ICONS",
    {
        "zip": "bi bi-file-zip",
        "x-tar": "bi bi-file-zip",
        "plain": "bi bi-filetype-txt",
        "jpeg": "bi bi-filetype-jpg",
        "svg+xml": "bi bi-filetype-svg",
        "xml": "bi bi-filetype-xml",
        "json": "bi bi-filetype-json",
        "png": "bi bi-filetype-png",
        "tiff": "bi bi-filetype-tiff",
        "pdf": "bi bi-filetype-pdf",
        "gif": "bi bi-filetype-gif",
        "csv": "bi bi-filetype-csv",
        "bmp": "bi bi-filetype-bmp",
        "vnd.openxmlformats-officedocument.wordprocessingml.document": "bi bi-filetype-doc",
        "msword": "bi bi-filetype-doc",
    },
)

# generated image thumbnail size in pixels - this is a tuple of maximum width
# and height - the aspect ratio will be preserved
SLM_THUMBNAIL_SIZE = env(
    "SLM_THUMBNAIL_SIZE", int, default=get_setting("SLM_THUMBNAIL_SIZE", 250)
)

# set this to either http or https, this will be used to determine the protocol
# of absolute uri links where a request object is not present
set_default("SLM_HTTP_PROTOCOL", "http" if DEBUG else "https")

# this should point to a cached property that holds the set of Django
# permissions relevant to the SLM - if you extend the permission set override
# this property
set_default("SLM_PERMISSIONS", "slm.authentication.default_permissions")

# These default permission groups will be created on migration
set_default(
    "SLM_DEFAULT_PERMISSION_GROUPS",
    {"Agency Manager": ["propose_sites", "moderate_sites"]},
)

# the xsd schemas that should be preloaded on start - if a schema is used
# that is not preloaded it will be lazily loaded which can take some time and
# will prolong the request. It can be useful to disable this during testing to
# reduce load times. It is recommended to leave this set to the default setting
# in production
set_default(
    "SLM_PRELOAD_SCHEMAS",
    []
    if DEBUG or get_setting("SLM_MANAGEMENT_MODE", False)
    else [geo for geo in GeodesyMLVersion],
)

# By default the SLM will not send moderation related emails to user accounts
# who have never logged in, set this to False to disable this behavior
# This does not apply to account related emails like password reset requests
set_default("SLM_EMAILS_REQUIRE_LOGIN", True)

# Automated alert configuration
#
set_default(
    "SLM_AUTOMATED_ALERTS",
    {
        "slm.GeodesyMLInvalid": {
            "issue": [
                "slm.signals.site_published",
                "slm.signals.site_file_published",
                "slm.signals.site_file_unpublished",
            ],
            "level": AlertLevel.ERROR,
            "send_email": False,
        },
        "slm.ReviewRequested": {
            "issue": ["slm.signals.review_requested"],
            "rescind": [
                "slm.signals.updates_rejected",
                "slm.signals.site_published",
                "slm.signals.section_added",
                "slm.signals.section_edited",
                "slm.signals.section_deleted",
            ],
            "level": AlertLevel.NOTICE,
            "send_email": True,
        },
        "slm.UpdatesRejected": {
            "issue": ["slm.signals.updates_rejected"],
            "rescind": [
                "slm.signals.review_requested",
                "slm.signals.site_published",
                "slm.signals.section_added",
                "slm.signals.section_edited",
                "slm.signals.section_deleted",
            ],
            "level": AlertLevel.ERROR,
            "send_email": True,
        },
        "slm.SiteLogPublished": {
            "issue": {"slm.signals.site_published"},
            "level": AlertLevel.NOTICE,
            "send_email": True,
        },
        "slm.UnpublishedFilesAlert": {
            "issue": {
                "slm.signals.site_file_uploaded",
                "slm.signals.site_file_unpublished",
            },
            "rescind": [
                "slm.signals.site_file_published",
                "slm.signals.site_file_deleted",
            ],
            "level": AlertLevel.NOTICE,
            "send_email": True,
        },
    },
)

# control the domain used to generate absolute links to the SLM log document
# attachments including images and files. Any standalone artifacts produced by
# the slm that include links to files served by the SLM will use this domain
# as the stem. If empty the default site domain will be used. You probably
# do not need to set this field unless you are serving files off a different
# instance than the instance that generates serialized artifacts
SLM_FILE_DOMAIN = None

SLM_IGS_STATION_NAMING = env(
    "SLM_IGS_STATION_NAMING", default=get_setting("SLM_IGS_STATION_NAMING", False)
)
if SLM_IGS_STATION_NAMING:
    # Use IGS naming rules for station names:
    SLM_STATION_NAME_REGEX = r"[\w]{4}[\d]{2}[\w]{3}"
    SLM_STATION_NAME_HELP = _(
        "This is the 9 Character station name (XXXXMRCCC) used in RINEX 3 "
        "filenames Format: (XXXX - existing four character IGS station "
        "name, M - Monument or marker number (0-9), R - Receiver number "
        "(0-9), CCC - Three digit ISO 3166-1 country code)"
    )
else:
    set_default("SLM_STATION_NAME_REGEX", None)
    set_default("SLM_STATION_NAME_HELP", _("The name of the station."))


# these settings control site log format precedence and naming
SLM_FORMAT_PRIORITY = {
    SiteLogFormat(fmt): int(priority)
    for fmt, priority in env(
        "SLM_FORMAT_PRIORITY", dict, default=get_setting("SLM_FORMAT_PRIORITY", {})
    )
}

priorities = SLM_FORMAT_PRIORITY or {fmt: fmt.value for fmt in SiteLogFormat}

SLM_DEFAULT_FORMAT = SiteLogFormat(
    env(
        "SLM_DEFAULT_FORMAT",
        str,
        max(priorities, key=priorities.get),
    )
)

SLM_FORMAT_EXTENSIONS = {
    **{fmt: fmt.ext for fmt in SiteLogFormat},
    **{
        SiteLogFormat(fmt): ext
        for fmt, ext in env(
            "SLM_FORMAT_EXTENSIONS",
            dict,
            default=get_setting(
                "SLM_FORMAT_EXTENSIONS", {fmt: fmt.ext for fmt in SiteLogFormat}
            ),
        ).items()
    },
}

# when logs are published, the following formats will be rendered to the site log index
SLM_ENABLED_FORMATS = [
    SiteLogFormat(fmt)
    for fmt in env(
        "SLM_ENABLED_FORMATS",
        list,
        default=get_setting(
            "SLM_ENABLED_FORMATS", [SiteLogFormat.ASCII_9CHAR, SiteLogFormat.GEODESY_ML]
        ),
    )
]

if SLM_DEFAULT_FORMAT not in SLM_ENABLED_FORMATS:
    SLM_ENABLED_FORMATS.insert(0, SLM_DEFAULT_FORMAT)


SLM_COORDINATE_MODE = CoordinateMode(
    env(
        "SLM_COORDINATE_MODE",
        default=get_setting("SLM_COORDINATE_MODE", CoordinateMode.INDEPENDENT),
    )
)
