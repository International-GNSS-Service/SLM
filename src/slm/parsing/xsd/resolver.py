from os import makedirs
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings
from lxml.etree import Resolver


class CachedResolver(Resolver):
    """
    Resolve remote schema imports from a local cache, fetching and caching them
    on first use. libxml2 (>=2.14) no longer fetches remote resources itself.
    """

    CACHE_DIR = Path(getattr(settings, "MEDIA_ROOT")) / "cache" / "xsd"

    def resolve(self, system_url, public_id, context):
        parsed = urlparse(system_url)
        if parsed.scheme not in {"http", "https"}:
            return None
        xsd_path = self.CACHE_DIR / parsed.netloc / parsed.path.lstrip("/")
        if not xsd_path.exists():
            response = requests.get(system_url, timeout=60)
            if response.status_code >= 300:
                return None
            makedirs(xsd_path.parent, exist_ok=True)
            xsd_path.write_bytes(response.content)
        # keep the remote url as the base so relative imports resolve back here
        return self.resolve_string(xsd_path.read_bytes(), context, base_url=system_url)
