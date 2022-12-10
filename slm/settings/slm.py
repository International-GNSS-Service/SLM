"""
SLM Specific Configuration parameters go here.
"""
from slm.defines import SiteFileUploadStatus, SiteLogStatus

SLM_STATUS_COLORS = {
    SiteLogStatus.DORMANT: '#3D4543',
    SiteLogStatus.PENDING: '#913D88',
    SiteLogStatus.UPDATED: '#8D6708',
    SiteLogStatus.PUBLISHED: '#008000',
    SiteLogStatus.EMPTY: '#00000000'
}

SLM_FILE_COLORS = {
    SiteFileUploadStatus.UNPUBLISHED: '#8D6708',
    SiteFileUploadStatus.PUBLISHED: '#008000',
    SiteFileUploadStatus.INVALID: '#8b0000',
    SiteFileUploadStatus.WARNINGS: '#8D6708',
    SiteFileUploadStatus.VALID: '#008000'
}

# if True, for subsections and missing sections, placeholder structures will
# be added to the logs
SLM_LEGACY_PLACEHOLDERS = True

# the maximum file upload size in Mega Bytes
SLM_MAX_UPLOAD_SIZE_MB = 100

# a map of file icons (css) from mimetype subtypes
SLM_FILE_ICONS = {
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

# generated image thumbnail size in pixels - this is a tuple of maximum width
# and height - the aspect ratio will be preserved
SLM_THUMBNAIL_SIZE = (250, 250)
