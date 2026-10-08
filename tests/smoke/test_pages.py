"""
Smoke tests: every HTML page renders for the users that should see it, and
redirects or refuses the ones that should not.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from slm.models import Agency, Alert, Network, Site
from slm.views import EditView

SITE_PAGES = [
    "slm:edit",
    "slm:upload",
    "slm:download",
    "slm:review",
    "slm:log",
    "slm:alerts",
]
GLOBAL_PAGES = [
    "slm:home",
    "slm:about",
    "slm:help",
    "slm:profile",
    "slm:alerts",
    "slm:user_activity",
    "slm:new_site",
    "slm_map:map",
]


def get(client, url, **kwargs):
    return client.get(url, secure=True, **kwargs)


@pytest.fixture
def client_for():
    def make(user=None):
        client = Client()
        if user:
            client.force_login(user)
        return client

    return make


@pytest.mark.parametrize("name", GLOBAL_PAGES)
def test_global_pages_require_login(db, client_for, name):
    response = get(client_for(), reverse(name))
    assert response.status_code == 302
    assert reverse("account_login") in response["Location"]


@pytest.mark.parametrize("name", GLOBAL_PAGES)
def test_global_pages_render(client_for, editor, published_site, name):
    response = get(client_for(editor), reverse(name))
    assert response.status_code == 200, response.content[:2000]


def test_map_by_agency(client_for, editor, published_site, agency_1):
    response = get(client_for(editor), reverse("slm_map:map", args=[agency_1.name]))
    assert response.status_code == 200


def test_home_lists_editable_sites(client_for, editor, published_site):
    response = get(client_for(editor), reverse("slm:home"))
    assert response.context["num_sites"] == 1


@pytest.mark.parametrize("name", SITE_PAGES)
def test_station_pages_render(client_for, editor, published_site, name):
    response = get(client_for(editor), reverse(name, args=[published_site.name]))
    assert response.status_code == 200, response.content[:2000]
    assert response.context["site"] == published_site


@pytest.mark.parametrize("name", SITE_PAGES)
def test_station_pages_render_updated(client_for, moderator, updated_site, name):
    response = get(client_for(moderator), reverse(name, args=[updated_site.name]))
    assert response.status_code == 200, response.content[:2000]
    assert response.context["is_moderator"]


@pytest.mark.parametrize("name", SITE_PAGES)
def test_station_pages_require_login(client_for, published_site, name):
    response = get(client_for(), reverse(name, args=[published_site.name]))
    assert response.status_code == 302


@pytest.mark.parametrize("name", SITE_PAGES)
def test_station_pages_forbidden_to_other_agency(
    client_for, other_editor, published_site, name
):
    response = get(client_for(other_editor), reverse(name, args=[published_site.name]))
    assert response.status_code in {403, 404}


@pytest.mark.parametrize("name", SITE_PAGES)
def test_station_pages_superuser(client_for, superuser, published_site, name):
    response = get(client_for(superuser), reverse(name, args=[published_site.name]))
    assert response.status_code == 200


@pytest.mark.parametrize("name", SITE_PAGES)
def test_station_pages_unknown_station(client_for, superuser, published_site, name):
    response = get(client_for(superuser), reverse(name, args=["ZZZ000ZZZ"]))
    assert response.status_code == 404


@pytest.mark.parametrize("section", list(EditView.FORMS.keys()))
def test_edit_sections_render(client_for, editor, published_site, section):
    response = get(
        client_for(editor), reverse("slm:edit", args=[published_site.name, section])
    )
    assert response.status_code == 200, response.content[:2000]
    assert response.context["forms"]


@pytest.mark.parametrize("section", list(EditView.FORMS.keys()))
def test_edit_sections_render_proposed(client_for, editor, proposed_site, section):
    response = get(
        client_for(editor), reverse("slm:edit", args=[proposed_site.name, section])
    )
    assert response.status_code == 200, response.content[:2000]


def test_review_at_epoch(client_for, moderator, published_site):
    # NOTE: DateTimeConverter.to_url emits a "+00:00" suffix for aware
    # datetimes which its own regex rejects, so reverse() with the datetime
    # itself fails - pass the naive string form the regex expects.
    epoch = published_site.last_publish.strftime("%Y-%m-%dT%H:%M:%S.%f")
    response = get(
        client_for(moderator), reverse("slm:review", args=[published_site.name, epoch])
    )
    assert response.status_code == 200


def test_upload_file_detail(client_for, editor, published_site):
    upload = published_site.sitefileuploads.first()
    assert upload is not None
    response = get(
        client_for(editor), reverse("slm:upload", args=[published_site.name, upload.pk])
    )
    assert response.status_code == 200
    response = get(
        client_for(editor), reverse("slm:upload", args=[published_site.name, 999999])
    )
    assert response.status_code == 404


def test_user_activity_for_other_user(client_for, editor, moderator, superuser):
    assert (
        get(
            client_for(superuser), reverse("slm:user_activity", args=[editor.pk])
        ).status_code
        == 200
    )
    assert get(
        client_for(editor), reverse("slm:user_activity", args=[moderator.pk])
    ).status_code in {403, 404}


def test_alert_detail(client_for, moderator, updated_site):
    # publishing issues alerts (e.g. SiteLogPublished) visible to moderators
    alerts = Alert.objects.visible_to(moderator)
    assert alerts.exists()
    for alert in alerts:
        response = get(client_for(moderator), reverse("slm:alert", args=[alert.pk]))
        assert response.status_code == 200


ADMIN_MODELS = [Site, Agency, Network, get_user_model(), Alert]


def test_admin_index(client_for, superuser):
    assert get(client_for(superuser), reverse("admin:index")).status_code == 200


@pytest.mark.parametrize(
    "model", ADMIN_MODELS, ids=[m._meta.model_name for m in ADMIN_MODELS]
)
def test_admin_changelists(client_for, superuser, published_site, model):
    url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
    assert get(client_for(superuser), url).status_code == 200


def test_admin_requires_staff(client_for, editor):
    response = get(client_for(editor), reverse("admin:index"))
    assert response.status_code == 302
