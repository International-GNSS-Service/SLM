from django.core.cache import cache
from django.dispatch import receiver

from slm import signals as slm_signals
from slm.defines import SiteFileUploadStatus


@receiver(slm_signals.site_published)
@receiver(slm_signals.site_file_published)
@receiver(slm_signals.site_file_unpublished)
def clear_default_cache(**_):
    """
    When events happen that change the public data of the SLM we clear our default cache.
    """
    cache.clear()


@receiver(slm_signals.site_file_deleted)
def clear_cache_if_published_file_deleted(sender, **kwargs):
    """
    If a site file attachment is deleted, only clear the caches if that file was published.
    """
    if file := kwargs.pop("upload", None):
        if file.status is SiteFileUploadStatus.PUBLISHED:
            cache.clear()
