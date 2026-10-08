"""
Smoke tests for the signal -> automated alert pipeline configured by
SLM_AUTOMATED_ALERTS.
"""

import pytest
from django.urls import reverse

from slm import signals as slm_signals
from slm.defines import SiteFileUploadStatus
from slm.models import (
    Alert,
    ReviewRequested,
    SiteFileUpload,
    SiteLogPublished,
    UnpublishedFilesAlert,
    UpdatesRejected,
)
from tests.conftest import publish_site, upload_file
from tests.resources import JPLM_JPG


@pytest.fixture(autouse=True)
def emails_without_login(settings):
    settings.SLM_EMAILS_REQUIRE_LOGIN = False


def request_review(client, site, detail="please review"):
    response = client.patch(
        reverse("slm_edit_api:request_review-detail", kwargs={"pk": site.pk}),
        {"detail": detail},
        format="json",
        secure=True,
    )
    assert response.status_code < 300, response.content[:2000]


def reject(client, site, detail="needs work"):
    response = client.patch(
        reverse("slm_edit_api:reject_updates-detail", kwargs={"pk": site.pk}),
        {"detail": detail},
        format="json",
        secure=True,
    )
    assert response.status_code < 300, response.content[:2000]


def edit(client, site):
    ident = site.siteidentification_set.head()
    response = client.post(
        reverse("slm_edit_api:siteidentification-list"),
        {
            "site": site.pk,
            "site_name": ident.site_name,
            "iers_domes_number": ident.iers_domes_number,
            "date_installed": ident.date_installed.isoformat(),
            "monument_height": (ident.monument_height or 0) + 1,
        },
        format="json",
        secure=True,
    )
    assert response.status_code < 300, response.content[:2000]


def test_site_published_alert(published_site):
    assert SiteLogPublished.objects.filter(site=published_site).exists()


def test_review_requested_alert_and_email(
    api_client, editor, moderator, updated_site, mailoutbox, signals
):
    request_review(api_client(editor), updated_site)
    assert slm_signals.review_requested in signals.signals
    alert = ReviewRequested.objects.get(site=updated_site)
    assert Alert.objects.visible_to(moderator).filter(pk=alert.pk).exists()
    assert any(moderator.email in mail.to for mail in mailoutbox)


def test_review_requested_rescinded_by_edit(api_client, editor, updated_site):
    request_review(api_client(editor), updated_site)
    assert ReviewRequested.objects.filter(site=updated_site).exists()
    edit(api_client(editor), updated_site)
    assert not ReviewRequested.objects.filter(site=updated_site).exists()


def test_review_requested_rescinded_by_publish(
    api_client, editor, moderator, updated_site
):
    request_review(api_client(editor), updated_site)
    publish_site(api_client(moderator), updated_site)
    assert not ReviewRequested.objects.filter(site=updated_site).exists()


def test_updates_rejected_alert_lifecycle(
    api_client, editor, moderator, updated_site, mailoutbox
):
    request_review(api_client(editor), updated_site)
    mailoutbox.clear()
    reject(api_client(moderator), updated_site)

    assert UpdatesRejected.objects.filter(site=updated_site).exists()
    assert not ReviewRequested.objects.filter(site=updated_site).exists()
    assert any(editor.email in mail.to for mail in mailoutbox)

    # requesting review again rescinds the rejection
    request_review(api_client(editor), updated_site)
    assert not UpdatesRejected.objects.filter(site=updated_site).exists()


def test_unpublished_files_alert(api_client, editor, moderator, published_site):
    upload_file(api_client(editor), published_site, JPLM_JPG, content_type="image/jpeg")
    assert UnpublishedFilesAlert.objects.filter(site=published_site).exists()

    upload = SiteFileUpload.objects.get(site=published_site, name=JPLM_JPG.name)
    api_client(moderator).patch(
        reverse(
            "slm_edit_api:files-detail",
            kwargs={"site": published_site.name, "pk": upload.pk},
        ),
        {"status": SiteFileUploadStatus.PUBLISHED.value},
        format="json",
        secure=True,
    )
    assert not UnpublishedFilesAlert.objects.filter(site=published_site).exists()


def test_alerts_scoped_to_agency(api_client, editor, other_editor, updated_site):
    request_review(api_client(editor), updated_site)
    alert = ReviewRequested.objects.get(site=updated_site)
    assert not Alert.objects.visible_to(other_editor).filter(pk=alert.pk).exists()


def test_alerts_page_lists_alert(api_client, client, editor, moderator, updated_site):
    request_review(api_client(editor), updated_site)
    client.force_login(moderator)
    response = client.get(reverse("slm:alerts"), secure=True)
    assert response.status_code == 200
    alert = ReviewRequested.objects.get(site=updated_site)
    response = client.get(reverse("slm:alert", args=[alert.pk]), secure=True)
    assert response.status_code == 200
