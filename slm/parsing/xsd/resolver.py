from os import makedirs
from os.path import exists
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings
from lxml.etree import Resolver


class CachedResolver(Resolver):
    CACHE_DIR = Path(getattr(settings, "MEDIA_ROOT")) / "cache" / "xsd"

    def resolve(self, system_url, public_id, context):
        parsed = urlparse(system_url)
        if parsed.scheme:
            xsd_path = self.CACHE_DIR / parsed.netloc / parsed.path.lstrip("/")
            makedirs(xsd_path.parent, exist_ok=True)
            if not exists(str(xsd_path)):
                response = requests.get(system_url)
                if response.status_code < 300:
                    system_url = xsd_path
                    with open(system_url, "wb") as f:
                        f.write(response.content)
            else:
                system_url = xsd_path

        return super().resolve(system_url, public_id, context)
