"""Signal handlers that cleanup filesystem artifacts"""

import os
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from slm.models import ArchivedSiteLog, GeodesyMLInvalid, SiteFile, SiteFileUpload


def cleanup(file_path):
    """
    Delete the given file and recursively walk up directories deleting
    directories, stopping at the first non-empty directory or MEDIA_ROOT
    """
    media_root = Path(settings.MEDIA_ROOT)
    file_path = Path(file_path)
    while file_path != media_root:
        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            if not os.listdir(str(file_path)):
                file_path.rmdir()
            else:
                break
        file_path = file_path.parent


@receiver(pre_delete, sender=ArchivedSiteLog)
@receiver(pre_delete, sender=SiteFileUpload)
@receiver(pre_delete, sender=SiteFile)
@receiver(pre_delete, sender=GeodesyMLInvalid)
def file_deleted(sender, instance, using, **kwargs):
    if os.path.exists(instance.file.path):
        transaction.on_commit(lambda: cleanup(instance.file.path))
    if hasattr(instance, "thumbnail") and instance.thumbnail:
        if os.path.exists(instance.thumbnail.path):
            transaction.on_commit(lambda: cleanup(instance.thumbnail.path))
