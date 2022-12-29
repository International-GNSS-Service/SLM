"""
SLM Specific Configuration parameters go here.
"""
from slm.defines import (
    SiteFileUploadStatus,
    SiteLogStatus,
    AlertLevel,
    GeodesyMLVersion
)
from slm.settings import set_default, is_defined
import os

# manage.py will set this to true if django has been loaded to run a
# management command
SLM_MANAGEMENT_MODE = os.environ.get('SLM_MANAGEMENT_FLAG', False) == 'ON'

set_default(
    'SLM_ALERT_COLORS', {
        AlertLevel.NOTICE: '#12CAF0',
        AlertLevel.WARNING: '#FFC106',
        AlertLevel.ERROR: '#DD3444'
    }
)

set_default(
    'SLM_STATUS_COLORS', {
        SiteLogStatus.DORMANT: '#3D4543',
        SiteLogStatus.NASCENT: '#913D88',
        SiteLogStatus.IN_REVIEW: '#0084BD',
        SiteLogStatus.UPDATED: '#8D6708',
        SiteLogStatus.PUBLISHED: '#0F980F',
        SiteLogStatus.EMPTY: '#D3D3D3'
    }
)

set_default(
    'SLM_FILE_COLORS', {
        SiteFileUploadStatus.UNPUBLISHED: '#8D6708',
        SiteFileUploadStatus.PUBLISHED: '#0F980F',
        SiteFileUploadStatus.INVALID: '#8b0000',
        SiteFileUploadStatus.WARNINGS: '#8D6708',
        SiteFileUploadStatus.VALID: '#0F980F'
    }
)

# if True, for subsections and missing sections, placeholder structures will
# be added to the logs
set_default('SLM_LEGACY_PLACEHOLDERS', True)

# the maximum file upload size in Mega Bytes
set_default('SLM_MAX_UPLOAD_SIZE_MB', 100)

# a map of file icons (css) from mimetype subtypes
set_default(
    'SLM_FILE_ICONS', {
        'zip': 'bi bi-file-zip',
        'x-tar': 'bi bi-file-zip',
        'plain': 'bi bi-filetype-txt',
        'jpeg': 'bi bi-filetype-jpg',
        'svg+xml': 'bi bi-filetype-svg',
        'xml': 'bi bi-filetype-xml',
        'json': 'bi bi-filetype-json',
        'png': 'bi bi-filetype-png',
        'tiff': 'bi bi-filetype-tiff',
        'pdf': 'bi bi-filetype-pdf',
        'gif': 'bi bi-filetype-gif',
        'csv': 'bi bi-filetype-csv',
        'bmp': 'bi bi-filetype-bmp',
        'vnd.openxmlformats-officedocument.wordprocessingml.document':
            'bi bi-filetype-doc',
        'msword': 'bi bi-filetype-doc'
    }
)

# generated image thumbnail size in pixels - this is a tuple of maximum width
# and height - the aspect ratio will be preserved
set_default('SLM_THUMBNAIL_SIZE', (250, 250))

# during deploy the current Site will be set to SLM_SITE_NAME, SLM_ORG_NAME
# The name of the organization used in communications
set_default('SLM_ORG_NAME', 'SLM')

set_default(
    'SLM_SITE_NAME',
    ALLOWED_HOSTS[0] if is_defined('ALLOWED_HOSTS') and ALLOWED_HOSTS
    else 'localhost'
)

# set this to either http or https, this will be used to determine the protocol
# of absolute uri links where a request object is not present
set_default('SLM_HTTP_PROTOCOL', None)

# this should point to a cached property that holds the set of Django
# permissions relevant to the SLM - if you extend the permission set override
# this property
set_default('SLM_PERMISSIONS', 'slm.authentication.default_permissions')

# These default permission groups will be created on migration
set_default(
    'SLM_DEFAULT_PERMISSION_GROUPS', {
        'Agency Manager': ['propose_sites', 'moderate_sites']
    }
)

# the xsd schemas that should be preloaded on start - if a schema is used
# that is not preloaded it will be lazily loaded which can take some time and
# will prolong the request. It can be useful to disable this during testing to
# reduce load times. It is recommended to leave this set to the default setting
# in production
set_default('SLM_PRELOAD_SCHEMAS', [geo for geo in GeodesyMLVersion])

# By default the SLM will not send moderation related emails to user accounts
# who have never logged in, set this to False to disable this behavior
# This does not apply to account related emails like password reset requests
set_default('SLM_EMAILS_REQUIRE_LOGIN', True)

# Automated alert configuration
#
set_default(
    'SLM_AUTOMATED_ALERTS', {
        'slm.GeodesyMLInvalid': {
            'signals': [
                'slm.signals.site_published',
                'slm.signals.site_file_published',
                'slm.signals.site_file_unpublished'
            ],
            'level': AlertLevel.ERROR,
            'send_email': False
        }
    }
)
