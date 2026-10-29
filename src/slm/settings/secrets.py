import os
from pathlib import Path

from slm.settings import env as settings_environment
from slm.settings import get_setting, slm_path_mk_dirs_must_exist

env = settings_environment()

SLM_SECRETS_DIR = env(
    "SLM_SECRETS_DIR",
    slm_path_mk_dirs_must_exist,
    default=get_setting("SLM_SECRETS_DIR", Path(get_setting("BASE_DIR")) / "secrets"),
)

SECRET_KEY = env("SECRET_KEY", default=get_setting("SECRET_KEY", None))
if not SECRET_KEY:
    sk_file = Path(SLM_SECRETS_DIR) / "secret_key"
    if not sk_file.is_file():
        from django.core.management.utils import get_random_secret_key

        SECRET_KEY = get_random_secret_key()
        try:
            # create the file with restrictive permissions from the start so it is
            # never world readable, and exclusively so concurrent workers starting
            # up at the same time end up sharing one key instead of each writing
            # their own
            fd = os.open(sk_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
        except FileExistsError:
            SECRET_KEY = sk_file.read_text().strip()
        else:
            with os.fdopen(fd, "w") as sk:
                sk.write(f"{SECRET_KEY}\n")
    else:
        SECRET_KEY = sk_file.read_text().strip()
