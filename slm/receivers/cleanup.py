""" Signal handlers that cleanup filesystem artifacts """
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from slm.models import SiteFileUpload
from django.db import transaction
from django.conf import settings
import os
from pathlib import Path


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


@receiver(pre_delete, sender=SiteFileUpload)
def file_deleted(sender, instance, using, **kwargs):
    transaction.on_commit(lambda: cleanup(instance.file.path))
