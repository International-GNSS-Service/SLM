from slm.settings import set_default

MEDIA_URL = '/media/'
set_default('MEDIA_ROOT', SITE_DIR / 'media')

# set RWX for Owner and Group for any uploaded files
FILE_UPLOAD_PERMISSIONS = 0o770
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o770
