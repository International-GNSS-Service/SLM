from slm.settings import env as settings_environment
from slm.settings import get_setting, set_default, slm_path_mk_dirs_must_exist

env = settings_environment()

set_default("MEDIA_URL", "/media/")

DEBUG = get_setting("DEBUG", False)

MEDIA_ROOT = env(
    "MEDIA_ROOT",
    slm_path_mk_dirs_must_exist,
    default=get_setting("MEDIA_ROOT", get_setting("BASE_DIR") / "media"),
)

FILE_UPLOAD_MAX_MEMORY_SIZE = env(
    "FILE_UPLOAD_MAX_MEMORY_SIZE",
    int,
    default=get_setting("FILE_UPLOAD_MAX_MEMORY_SIZE", 2621440),
)

# set RWX for Owner and Group for any uploaded files
FILE_UPLOAD_PERMISSIONS = env(
    "FILE_UPLOAD_PERMISSIONS",
    int,
    default=get_setting("FILE_UPLOAD_PERMISSIONS", 0o664 if DEBUG else 0o660),
)
FILE_UPLOAD_DIRECTORY_PERMISSIONS = env(
    "FILE_UPLOAD_DIRECTORY_PERMISSIONS",
    int,
    default=get_setting("FILE_UPLOAD_DIRECTORY_PERMISSIONS", 0o775 if DEBUG else 0o770),
)

FILE_UPLOAD_TEMP_DIR = env(
    "FILE_UPLOAD_TEMP_DIR", str, default=get_setting("FILE_UPLOAD_TEMP_DIR", None)
)
