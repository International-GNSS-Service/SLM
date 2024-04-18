import os
from pathlib import Path

from slm.settings import get_setting

SLM_SECRETS_DIR = get_setting(
    "SLM_SECRETS_DIR", Path(get_setting("SITE_DIR")) / "secrets"
)


def generate_secret_key(filename):
    from django.core.management.utils import get_random_secret_key

    with open(filename, "w") as f:
        f.write("%s\n" % get_random_secret_key())
    os.chmod(filename, 0o640)


def get_secret_key(filename):
    with open(filename, "r") as f:
        return f.readlines()[0]


if not os.path.exists(SLM_SECRETS_DIR):
    os.makedirs(SLM_SECRETS_DIR)


sk_file = os.path.join(SLM_SECRETS_DIR, "secret_key")

if not os.path.exists(sk_file):
    generate_secret_key(sk_file)

SECRET_KEY = get_secret_key(sk_file)

if len(SECRET_KEY) == 0:
    generate_secret_key(sk_file)
    SECRET_KEY = get_secret_key(sk_file)
