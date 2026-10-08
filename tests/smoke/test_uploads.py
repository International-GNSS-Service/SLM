"""
Smoke tests for site file uploads: site logs (legacy + GeodesyML), images and
attachments, plus the image operations endpoint.
"""

from pathlib import Path

import pytest
from django.urls import reverse

from slm import signals as slm_signals
from slm.defines import SiteFileUploadStatus, SiteLogStatus, SLMFileType
from slm.models import SiteFileUpload
from tests.conftest import upload_file
from tests.resources import (
    AAA600USA_LOG,
    ATTACHMENT_PDF,
    GML_05,
    JPLM_JPG,
    MALFORMED_LOG,
)

from .test_public_api import rows


def files_url(site, pk=None):
    if pk is None:
        return reverse("slm_edit_api:files-list", kwargs={"site": site.name})
    return reverse("slm_edit_api:files-detail", kwargs={"site": site.name, "pk": pk})


def errors(upload):
    return {
        line: message
        for line, (level, message, _) in upload.context["findings"].items()
        if level == "E"
    }


def test_legacy_upload_wrong_site_name(api_client, editor, proposed_site):
    response = upload_file(api_client(editor), proposed_site, AAA600USA_LOG)
    assert response.status_code == 400
    upload = SiteFileUpload.objects.get(site=proposed_site)
    assert upload.status == SiteFileUploadStatus.INVALID
    assert "Expected site name" in " ".join(errors(upload).values())
    assert proposed_site.siteidentification_set.count() == 0


def test_legacy_upload_stale_log_rejected(api_client, editor, published_site, signals):
    # re-uploading the already published log must be rejected as out of date
    signals.clear()
    response = upload_file(api_client(editor), published_site, AAA600USA_LOG)
    assert response.status_code == 400
    upload = SiteFileUpload.objects.get(pk=response.json()["file"])
    assert upload.file_type == SLMFileType.SITE_LOG
    assert upload.status == SiteFileUploadStatus.INVALID
    assert "Date prepared cannot be before the previous log." in errors(upload).values()
    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.PUBLISHED


def test_malformed_log_reports_findings(api_client, editor, proposed_site):
    response = upload_file(api_client(editor), proposed_site, MALFORMED_LOG)
    assert response.status_code == 400, response.content[:2000]
    upload = SiteFileUpload.objects.get(site=proposed_site)
    assert upload.status == SiteFileUploadStatus.INVALID
    # the bad X coordinate and latitude lines are flagged (keys are 0-indexed)
    assert {"44", "47"} <= set(errors(upload))
    # nothing should have been applied
    assert proposed_site.siteidentification_set.count() == 0


@pytest.mark.xfail(
    strict=True,
    reason="BUG: an impossible Date Installed (2023-13-45T99:99Z) produces no "
    "parser finding at all.",
)
def test_malformed_log_flags_invalid_date(api_client, editor, proposed_site):
    upload_file(api_client(editor), proposed_site, MALFORMED_LOG)
    upload = SiteFileUpload.objects.get(site=proposed_site)
    assert "27" in upload.context["findings"]


def test_geodesyml_upload(api_client, editor, proposed_site):
    response = upload_file(
        api_client(editor), proposed_site, GML_05, content_type="application/xml"
    )
    assert response.status_code < 500, response.content[:2000]
    upload = SiteFileUpload.objects.get(site=proposed_site)
    assert upload.file_type == SLMFileType.SITE_LOG


def test_image_upload_and_publish(api_client, editor, moderator, published_site):
    response = upload_file(
        api_client(editor), published_site, JPLM_JPG, content_type="image/jpeg"
    )
    assert response.status_code < 400, response.content[:2000]
    upload = SiteFileUpload.objects.get(site=published_site, name=JPLM_JPG.name)
    assert upload.file_type == SLMFileType.SITE_IMAGE
    assert upload.status == SiteFileUploadStatus.UNPUBLISHED
    assert Path(upload.thumbnail.path).stat().st_size > 0

    # not public until published
    public = rows(api_client().get(reverse("slm_public_api:files-list"), secure=True))
    assert upload.pk not in [row["id"] for row in public]

    response = api_client(moderator).patch(
        files_url(published_site, upload.pk),
        {"status": SiteFileUploadStatus.PUBLISHED.value},
        format="json",
        secure=True,
    )
    assert response.status_code < 400, response.content[:2000]
    upload.refresh_from_db()
    assert upload.status == SiteFileUploadStatus.PUBLISHED

    public = rows(api_client().get(reverse("slm_public_api:files-list"), secure=True))
    assert upload.pk in [row["id"] for row in public]
    response = api_client().get(
        reverse("slm_public_api:files-detail", kwargs={"pk": upload.pk}), secure=True
    )
    assert response.status_code == 200


def test_image_rotate(api_client, editor, other_editor, published_site):
    upload_file(api_client(editor), published_site, JPLM_JPG, content_type="image/jpeg")
    upload = SiteFileUpload.objects.get(site=published_site, name=JPLM_JPG.name)
    url = reverse("slm_edit_api:image-detail", kwargs={"pk": upload.pk})

    before = Path(upload.file.path).read_bytes()
    response = api_client(editor).get(url, {"rotate": 90}, secure=True)
    assert response.status_code == 204
    upload.refresh_from_db()
    assert Path(upload.file.path).read_bytes() != before

    assert api_client(editor).get(url, {"rotate": "x"}, secure=True).status_code == 400
    assert api_client(other_editor).get(
        url, {"rotate": 90}, secure=True
    ).status_code in {
        403,
        404,
    }


def test_attachment_upload(api_client, editor, published_site):
    response = upload_file(
        api_client(editor),
        published_site,
        ATTACHMENT_PDF,
        content_type="application/pdf",
    )
    assert response.status_code < 400, response.content[:2000]
    upload = SiteFileUpload.objects.get(site=published_site, name=ATTACHMENT_PDF.name)
    assert upload.file_type == SLMFileType.ATTACHMENT


def test_file_list_and_delete(api_client, editor, published_site, signals):
    client = api_client(editor)
    upload_file(client, published_site, ATTACHMENT_PDF, content_type="application/pdf")
    listed = rows(client.get(files_url(published_site), secure=True))
    names = [row["name"] for row in listed]
    assert ATTACHMENT_PDF.name in names
    assert AAA600USA_LOG.name in names

    filtered = rows(
        client.get(
            files_url(published_site),
            {"file_type": SLMFileType.ATTACHMENT.value},
            secure=True,
        )
    )
    assert [row["name"] for row in filtered] == [ATTACHMENT_PDF.name]

    pk = filtered[0]["id"]
    signals.clear()
    response = client.delete(files_url(published_site, pk), secure=True)
    assert response.status_code < 300
    assert slm_signals.site_file_deleted in signals.signals
    assert not SiteFileUpload.objects.filter(pk=pk).exists()


def test_upload_forbidden_to_other_agency(api_client, other_editor, published_site):
    response = upload_file(api_client(other_editor), published_site, AAA600USA_LOG)
    assert response.status_code == 403
    response = api_client(other_editor).get(files_url(published_site), secure=True)
    assert response.status_code == 403


def test_upload_unknown_site(api_client, editor, db):
    response = api_client(editor).get(
        reverse("slm_edit_api:files-list", kwargs={"site": "ZZZ000ZZZ"}), secure=True
    )
    assert response.status_code == 404


def test_upload_page_shows_file(client, editor, published_site):
    client.force_login(editor)
    upload = SiteFileUpload.objects.filter(site=published_site).first()
    response = client.get(
        reverse("slm:upload", args=[published_site.name, upload.pk]), secure=True
    )
    assert response.status_code == 200
    assert upload.name.encode() in response.content
