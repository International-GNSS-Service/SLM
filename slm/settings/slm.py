"""
SLM Specific Configuration parameters go here.
"""

import os

from slm.defines import (
    AlertLevel,
    GeodesyMLVersion,
    SiteFileUploadStatus,
    SiteLogStatus,
)
from slm.settings import get_setting, set_default

# manage.py will set this to true if django has been loaded to run a
# management command
SLM_MANAGEMENT_MODE = os.environ.get("SLM_MANAGEMENT_FLAG", False) == "ON"

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
set_default("SLM_LEGACY_PLACEHOLDERS", True)

# the maximum file upload size in Mega Bytes
set_default("SLM_MAX_UPLOAD_SIZE_MB", 100)

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
set_default("SLM_THUMBNAIL_SIZE", 250)

# during deploy the current Site will be set to SLM_SITE_NAME, SLM_ORG_NAME
# The name of the organization used in communications
set_default("SLM_ORG_NAME", "SLM")

set_default("SLM_SITE_NAME", (get_setting("ALLOWED_HOSTS", []) or ["localhost"])[0])

# set this to either http or https, this will be used to determine the protocol
# of absolute uri links where a request object is not present
set_default("SLM_HTTP_PROTOCOL", None)

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
set_default("SLM_PRELOAD_SCHEMAS", [geo for geo in GeodesyMLVersion])

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

# slm provides an implementation of urls.py that will load this list into
# url patterns. This should be a list of 2-tuples where the first tuple is the
# path stem mount point for the included apps' URLs and the second element is
# the string that will be passed to django.urls.include
SLM_URL_MOUNTS = []


# control the domain used to generate absolute links to the SLM log document
# attachments including images and files. Any standalone artifacts produced by
# the slm that include links to files served by the SLM will use this domain
# as the stem. If empty the default site domain will be used. You probably
# do not need to set this field unless you are serving files off a different
# instance than the instance that generates serialized artifacts
SLM_FILE_DOMAIN = None
