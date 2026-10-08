"""
Smoke tests for the authenticated edit API under /api/edit/.
"""

import pytest
from django.urls import reverse

from slm import signals as slm_signals
from slm.api.edit import views as edit_views
from slm.defines import SiteLogStatus
from slm.models import Alert, LogEntry, Site, SiteSubSection

from .test_public_api import rows

SECTION_VIEWSETS = {
    view.serializer_class.Meta.model: view
    for view in vars(edit_views).values()
    if type(view) is edit_views.SectionViewSet
}
SECTIONS = sorted((model.__name__.lower(), model) for model in SECTION_VIEWSETS.keys())
SECTION_IDS = [name for name, _ in SECTIONS]

# read only / bookkeeping fields that are not posted back when editing
META_FIELDS = {"_flags", "_diff", "can_publish", "published", "is_deleted", "id"}


def url(name, **kwargs):
    return reverse(f"slm_edit_api:{name}", kwargs=kwargs)


def post(client, name, data, **kwargs):
    return client.post(url(name, **kwargs), data=data, format="json", secure=True)


def patch(client, name, data, **kwargs):
    return client.patch(url(name, **kwargs), data=data, format="json", secure=True)


def editable(row):
    return {
        key: value
        for key, value in row.items()
        if key not in META_FIELDS and value is not None
    }


def section_rows(client, section, site):
    response = client.get(url(f"{section}-list"), {"site": site.name}, secure=True)
    assert response.status_code == 200, response.content[:2000]
    return rows(response)


###############################################################################
# Access control


@pytest.mark.parametrize("section", SECTION_IDS)
def test_sections_require_auth(api_client, published_site, section):
    response = api_client().get(url(f"{section}-list"), secure=True)
    assert response.status_code in {401, 403}


@pytest.mark.parametrize("section,model", SECTIONS, ids=SECTION_IDS)
def test_section_list(api_client, editor, published_site, section, model):
    found = section_rows(api_client(editor), section, published_site)
    expected = model.objects.station(published_site).head()
    if issubclass(model, SiteSubSection):
        assert len(found) >= expected.count()
    else:
        assert len(found) == (1 if expected else 0)


def test_section_list_hidden_from_other_agency(
    api_client, other_editor, published_site
):
    assert (
        section_rows(api_client(other_editor), "siteidentification", published_site)
        == []
    )


@pytest.mark.xfail(
    strict=True,
    reason="BUG (authz): POSTing to a section list endpoint only requires "
    "authentication - perform_section_update never checks site.can_edit(), so "
    "a user from another agency can edit (but not publish) any site's sections.",
)
def test_other_agency_cannot_edit(api_client, other_editor, editor, published_site):
    row = section_rows(api_client(editor), "siteidentification", published_site)[0]
    response = post(
        api_client(other_editor),
        "siteidentification-list",
        {**editable(row), "monument_height": 9.9},
    )
    assert response.status_code in {403, 404}
    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.PUBLISHED


def test_other_agency_cannot_edit_detail(
    api_client, other_editor, editor, published_site
):
    row = section_rows(api_client(editor), "siteidentification", published_site)[0]
    response = patch(
        api_client(other_editor),
        "siteidentification-detail",
        {"monument_height": 9.9},
        pk=row["id"],
    )
    assert response.status_code in {403, 404}


###############################################################################
# Section editing


def _sections_with_data():
    """Sections populated by the AAA600USA fixture log."""
    return [
        "siteform",
        "siteidentification",
        "sitelocation",
        "sitereceiver",
        "siteantenna",
        "sitefrequencystandard",
        "sitehumiditysensor",
        "sitemultipathsources",
        "siteoperationalcontact",
        "siteresponsibleagency",
        "sitemoreinformation",
    ]


def _tweak(row):
    """Make a harmless edit to a serialized section."""
    data = editable(row)
    for field in ("additional_information", "additional_info", "notes", "prepared_by"):
        if field in row:
            data[field] = f"{row[field] or ''} smoke test edit".strip()
            return data, field
    raise AssertionError(f"No editable free text field in {sorted(row)}")


@pytest.mark.parametrize("section", _sections_with_data())
def test_section_edit_marks_site_updated(
    api_client, editor, published_site, signals, section
):
    client = api_client(editor)
    row = section_rows(client, section, published_site)[0]
    data, field = _tweak(row)
    signals.clear()
    response = post(client, f"{section}-list", data)
    assert response.status_code < 300, response.content[:2000]
    assert response.json()[field] == data[field]
    assert slm_signals.section_edited in signals.signals

    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.UPDATED

    # the published version is still served to the public
    response = client.get(
        url(f"{section}-list"), {"site": published_site.name}, secure=True
    )
    assert response.status_code == 200


@pytest.mark.parametrize("section", _sections_with_data())
def test_section_publish_requires_moderator(
    api_client, editor, moderator, published_site, section
):
    row = section_rows(api_client(editor), section, published_site)[0]
    data, _ = _tweak(row)
    response = post(api_client(editor), f"{section}-list", {**data, "publish": True})
    assert response.status_code == 403

    response = post(api_client(moderator), f"{section}-list", {**data, "publish": True})
    assert response.status_code < 300, response.content[:2000]
    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.PUBLISHED


@pytest.mark.parametrize("section", ["sitereceiver", "sitehumiditysensor"])
def test_subsection_delete(api_client, editor, published_site, signals, section):
    client = api_client(editor)
    row = section_rows(client, section, published_site)[0]
    signals.clear()
    response = client.delete(url(f"{section}-detail", pk=row["id"]), secure=True)
    assert response.status_code < 300, response.content[:2000]
    assert slm_signals.section_deleted in signals.signals
    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.UPDATED


def test_revert_section_edit(api_client, editor, published_site):
    client = api_client(editor)
    row = section_rows(client, "siteidentification", published_site)[0]
    data, _ = _tweak(row)
    edited = post(client, "siteidentification-list", data).json()
    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.UPDATED

    response = post(
        client, "siteidentification-list", {**editable(edited), "revert": True}
    )
    assert response.status_code < 300, response.content[:2000]
    # the unpublished edit is discarded and the published row is head again
    # (the site stays UPDATED because editing also touched the siteform section)
    assert response.json()["published"] is True
    assert published_site.siteidentification_set.filter(published=False).count() == 0
    assert "smoke test edit" not in (
        published_site.siteidentification_set.head().additional_information
    )


def test_invalid_section_data_rejected(api_client, editor, published_site):
    client = api_client(editor)
    row = section_rows(client, "sitelocation", published_site)[0]
    response = post(client, "sitelocation-list", {**editable(row), "xyz": "not xyz"})
    assert response.status_code == 400


###############################################################################
# Stations


def test_station_list(api_client, editor, other_editor, superuser, published_site):
    def names(user):
        return [
            row["name"]
            for row in rows(api_client(user).get(url("stations-list"), secure=True))
        ]

    assert published_site.name in names(editor)
    assert published_site.name in names(superuser)
    assert published_site.name not in names(other_editor)


def test_station_list_ordering_and_filter(
    api_client, editor, published_site, proposed_site
):
    client = api_client(editor)
    found = rows(client.get(url("stations-list"), {"ordering": "-name"}, secure=True))
    assert [row["name"] for row in found] == [published_site.name, proposed_site.name]
    found = rows(
        client.get(
            url("stations-list"),
            {"status": SiteLogStatus.PROPOSED.value},
            secure=True,
        )
    )
    assert [row["name"] for row in found] == [proposed_site.name]


def test_station_propose_requires_permission(api_client, agency_1, published_site):
    from tests.conftest import make_user

    nobody = make_user("nobody@example.com", agency_1)
    response = post(
        api_client(nobody),
        "stations-list",
        {"name": "AAA900USA", "agencies": [{"id": agency_1.id}]},
    )
    assert response.status_code == 403


def test_station_publish(api_client, editor, moderator, updated_site, signals):
    response = patch(
        api_client(editor), "stations-detail", {"publish": True}, pk=updated_site.pk
    )
    assert response.status_code == 403

    signals.clear()
    response = patch(
        api_client(moderator), "stations-detail", {"publish": True}, pk=updated_site.pk
    )
    assert response.status_code < 300
    updated_site.refresh_from_db()
    assert updated_site.status == SiteLogStatus.PUBLISHED
    assert slm_signals.site_published in signals.signals


###############################################################################
# Review workflow


def has_review_request(site):
    # review_requested is a reverse one-to-one - re-fetch to avoid the cache
    return hasattr(Site.objects.get(pk=site.pk), "review_requested")


def test_review_request_and_reject(
    api_client, editor, moderator, updated_site, signals
):
    signals.clear()
    pending = rows(api_client(editor).get(url("request_review-list"), secure=True))
    assert updated_site.name in [row["name"] for row in pending]

    response = patch(
        api_client(editor),
        "request_review-detail",
        {"detail": "please review"},
        pk=updated_site.pk,
    )
    assert response.status_code < 300, response.content[:2000]
    assert slm_signals.review_requested in signals.signals
    assert has_review_request(updated_site)

    # the moderator sees the request and an alert
    to_review = rows(api_client(moderator).get(url("reject_updates-list"), secure=True))
    assert updated_site.name in [row["name"] for row in to_review]
    assert Alert.objects.visible_to(moderator).for_site(updated_site).exists()

    # editors cannot reject their own requests
    response = patch(
        api_client(editor),
        "reject_updates-detail",
        {"detail": "no"},
        pk=updated_site.pk,
    )
    assert response.status_code in {403, 404}

    signals.clear()
    response = patch(
        api_client(moderator),
        "reject_updates-detail",
        {"detail": "needs work"},
        pk=updated_site.pk,
    )
    assert response.status_code < 300, response.content[:2000]
    assert slm_signals.updates_rejected in signals.signals
    assert not has_review_request(updated_site)
    assert Site.objects.get(pk=updated_site.pk).updates_rejected is not None


def test_review_request_then_publish(api_client, editor, moderator, updated_site):
    patch(
        api_client(editor),
        "request_review-detail",
        {"detail": "go"},
        pk=updated_site.pk,
    )
    patch(
        api_client(moderator), "stations-detail", {"publish": True}, pk=updated_site.pk
    )
    updated_site.refresh_from_db()
    assert updated_site.status == SiteLogStatus.PUBLISHED
    assert not has_review_request(updated_site)


###############################################################################
# Alerts, log entries, profile


def test_alerts_list_and_dismiss(api_client, editor, moderator, updated_site):
    patch(
        api_client(editor),
        "request_review-detail",
        {"detail": "go"},
        pk=updated_site.pk,
    )
    client = api_client(moderator)
    alerts = rows(client.get(url("alerts-list"), secure=True))
    assert alerts
    assert rows(
        client.get(url("alerts-list"), {"site": updated_site.name}, secure=True)
    )

    alert_id = alerts[0]["id"]
    assert client.get(url("alerts-detail", pk=alert_id), secure=True).status_code == 200
    response = client.delete(url("alerts-detail", pk=alert_id), secure=True)
    assert response.status_code < 300
    assert not Alert.objects.filter(pk=alert_id).exists()


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="BUG: AlertFilter.for_user calls get_user_model().filter() instead "
    "of get_user_model().objects.filter().",
)
def test_alerts_filter_by_user(api_client, moderator, updated_site):
    response = api_client(moderator).get(
        url("alerts-list"), {"user": moderator.email}, secure=True
    )
    assert response.status_code == 200


def test_log_entries(api_client, editor, other_editor, updated_site):
    client = api_client(editor)
    entries = rows(client.get(url("logentries-list"), secure=True))
    assert entries
    assert LogEntry.objects.filter(site=updated_site).exists()
    filtered = rows(
        client.get(url("logentries-list"), {"site": updated_site.name}, secure=True)
    )
    assert filtered
    assert rows(api_client(other_editor).get(url("logentries-list"), secure=True)) == []


def test_profile_get_and_update(api_client, editor):
    client = api_client(editor)
    response = client.get(url("profile-list"), secure=True)
    assert response.status_code == 200
    assert response.json()["email"] == editor.email

    response = patch(client, "profile-detail", {"first_name": "Renamed"}, pk=editor.pk)
    assert response.status_code < 300, response.content[:2000]
    editor.refresh_from_db()
    assert editor.first_name == "Renamed"


def test_profile_cannot_update_other_user(api_client, editor, moderator):
    response = patch(
        api_client(editor), "profile-detail", {"first_name": "Hacked"}, pk=moderator.pk
    )
    assert response.status_code in {403, 404}
    moderator.refresh_from_db()
    assert moderator.first_name != "Hacked"


@pytest.mark.parametrize("endpoint", ["agency", "network"])
def test_agency_network_lists(api_client, editor, published_site, endpoint):
    response = api_client(editor).get(url(f"{endpoint}-list"), secure=True)
    assert response.status_code == 200
    rows(response)


@pytest.mark.parametrize("fmt", ["log", "xml"])
def test_download_unpublished_head(api_client, editor, updated_site, fmt):
    response = api_client(editor).get(
        reverse(
            "slm_edit_api:download-detail",
            kwargs={"site": updated_site.name, "format": fmt},
        ),
        {"unpublished": True},
        secure=True,
    )
    assert response.status_code == 200
    body = b"".join(response.streaming_content).decode()
    assert "smoke test" not in body  # sanity: updated_site edits monument height
    assert updated_site.name[:4].upper() in body.upper()


def test_edit_api_root(api_client, editor):
    assert api_client(editor).get(url("api-root"), secure=True).status_code == 200


def test_site_queryset_editable_by(editor, other_editor, published_site):
    assert published_site in Site.objects.editable_by(editor)
    assert published_site not in Site.objects.editable_by(other_editor)
