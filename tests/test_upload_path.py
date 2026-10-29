"""
site_upload_path builds the on disk location of site files from the site name
and the uploaded filename. The collision check must go through the field's
storage backend so that any path escaping the storage root is refused by
Django's safe_join rather than silently probed.
"""

import pytest
from django.core.exceptions import SuspiciousFileOperation

from slm.models import Site, SiteFileUpload
from slm.models.system import site_upload_path


def test_upload_path_is_under_the_site_directory():
    upload = SiteFileUpload(site=Site(name="AAA200USA"))
    assert site_upload_path(upload, "photo.jpg") == "uploads/AAA200USA/photo.jpg"


def test_upload_path_refuses_to_probe_outside_storage_root():
    upload = SiteFileUpload(site=Site(name="../../escape"))
    with pytest.raises(SuspiciousFileOperation):
        site_upload_path(upload, "photo.jpg")
