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

        os.makedirs(SLM_SECRETS_DIR, exist_ok=True)
        SECRET_KEY = get_random_secret_key()
        sk_file.write_text(f"{SECRET_KEY}\n")
        sk_file.chmod(0o640)
    else:
        SECRET_KEY = sk_file.read_text().strip()
