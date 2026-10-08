"""
Shared pytest fixtures for the SLM test suite.

Fixtures are layered so tests only pay for what they use:

    reference data -> users -> sites (in each lifecycle state) -> browser

Sites are built through the real edit API (upload + publish) rather than by
inserting rows directly so that signals, alerts and status bookkeeping are
exercised the same way they are in production.
"""

import inspect

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.dispatch import Signal
from django.urls import reverse
from rest_framework.test import APIClient

from slm import signals as slm_signals
from slm.defines import EquipmentState, SiteLogStatus
from slm.models import (
    Agency,
    Antenna,
    Manufacturer,
    Network,
    Radome,
    Receiver,
    Site,
)
from tests.resources import AAA600USA_LOG

PASSWORD = "password"


###############################################################################
# Builders - plain functions so the e2e suite can reuse them with a
# transactional database.


def make_user(email, agency=None, perms=(), superuser=False):
    User = get_user_model()
    if superuser:
        return User.objects.create_superuser(
            email=email, password=PASSWORD, first_name="Test", last_name="Super"
        )
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name="Test",
        last_name=email.split("@")[0].title(),
    )
    if agency:
        user.agencies.add(agency)
    for codename in perms:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


def logged_in_client(user=None):
    client = APIClient()
    if user is not None:
        client.force_login(user)
    return client


def create_site(client, name, agency):
    response = client.post(
        reverse("slm_edit_api:stations-list"),
        data={"name": name, "agencies": [{"id": agency.id}]},
        format="json",
        secure=True,
    )
    assert response.status_code < 300, response.content
    return Site.objects.get(name=name)


def upload_file(client, site, path, content_type="text/plain", name=None):
    return client.post(
        reverse("slm_edit_api:files-list", kwargs={"site": site.name}),
        {
            "file": SimpleUploadedFile(
                name or path.name, path.read_bytes(), content_type=content_type
            )
        },
        format="multipart",
        secure=True,
    )


def publish_site(client, site):
    response = client.patch(
        reverse("slm_edit_api:stations-detail", kwargs={"pk": site.pk}),
        data={"publish": True},
        format="json",
        secure=True,
    )
    assert response.status_code < 300, response.content
    site.refresh_from_db()
    return site


def _upload_errors(response):
    from slm.models import SiteFileUpload

    upload = SiteFileUpload.objects.filter(pk=response.json().get("file")).first()
    findings = (upload.context or {}).get("findings", {}) if upload else {}
    return {line: f for line, f in findings.items() if f[0] == "E"} or response.content


def build_seed():
    """
    Build the shared reference data, users and a published site.

    Returns a dict of primary keys - function scoped fixtures re-fetch the
    objects so no test sees another test's in-memory state.
    """
    agency_1 = Agency.objects.create(name="Test Agency 1", shortname="TA1")
    agency_2 = Agency.objects.create(name="Test Agency 2", shortname="TA2")
    network_1 = Network.objects.create(name="Test Network 1")
    network_2 = Network.objects.create(name="Test Network 2")

    # the equipment codings referenced by the fixture site logs
    javad = Manufacturer.objects.create(name="JAVAD GNSS", full_name="JAVAD GNSS")
    receiver = Receiver.objects.create(
        model="JAVAD TRE_3 DELTA", manufacturer=javad, state=EquipmentState.ACTIVE
    )
    antenna = Antenna.objects.create(
        model="JAV_GRANT-G3T", manufacturer=javad, state=EquipmentState.ACTIVE
    )
    radome = Radome.objects.create(
        model="JVDM", manufacturer=javad, state=EquipmentState.ACTIVE
    )

    # agency 1 member who can propose sites but not publish them
    editor = make_user("editor@example.com", agency_1, perms=["propose_sites"])
    # agency 1 member with moderate (publish) permission
    moderator = make_user(
        "moderator@example.com", agency_1, perms=["propose_sites", "moderate_sites"]
    )
    # agency 2 member - must not be able to touch agency 1 sites
    other_editor = make_user("other@example.com", agency_2, perms=["propose_sites"])
    superuser = make_user("superuser@example.com", superuser=True)

    # AAA600USA uploaded by the editor and published by the moderator
    client = logged_in_client(editor)
    site = create_site(client, "AAA600USA", agency_1)
    response = upload_file(client, site, AAA600USA_LOG)
    assert response.status_code < 400, _upload_errors(response)
    site = publish_site(logged_in_client(moderator), site)
    assert site.status == SiteLogStatus.PUBLISHED
    network_1.sites.add(site)

    return {
        "agency_1": agency_1.pk,
        "agency_2": agency_2.pk,
        "network_1": network_1.pk,
        "network_2": network_2.pk,
        "manufacturer": javad.pk,
        "receiver": receiver.pk,
        "antenna": antenna.pk,
        "radome": radome.pk,
        "editor": editor.pk,
        "moderator": moderator.pk,
        "other_editor": other_editor.pk,
        "superuser": superuser.pk,
        "published_site": site.pk,
    }


###############################################################################
# Seed data
#
# Building a published site runs ~1500 queries, so it is done once per test
# module inside an outer transaction that is rolled back when the module
# finishes. Each test still runs in its own savepoint (the ``db`` fixture), so
# tests are isolated from each other and from modules that do not use the
# seed (e.g. the TestCase classes that create the same names in setUp).
#
# Note: once any test in a module has requested ``seed`` its data is visible
# to every later test in that module, even ones that only request ``db``.
#
# This does not work with ``transactional_db``/``live_server`` - the e2e
# package overrides ``seed`` to build per-test instead.


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup):
    """
    Capture the serialized snapshot of the freshly migrated test database.

    Django keeps it on the connection object, but connections are context
    local and Playwright's sync API runs tests in a different context - so the
    e2e suite gets a fresh connection without the snapshot and serialized
    rollback silently restores nothing. The e2e conftest re-attaches it.
    """
    from django.db import connections

    return {
        alias: connections[alias]._test_serialized_contents
        for alias in connections
        if hasattr(connections[alias], "_test_serialized_contents")
    }


@pytest.fixture(scope="module")
def seed(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        atomic = transaction.atomic()
        atomic.__enter__()
        try:
            yield build_seed()
        finally:
            transaction.set_rollback(True)
            atomic.__exit__(None, None, None)


@pytest.fixture
def agency_1(seed, db):
    return Agency.objects.get(pk=seed["agency_1"])


@pytest.fixture
def agency_2(seed, db):
    return Agency.objects.get(pk=seed["agency_2"])


@pytest.fixture
def network_1(seed, db):
    return Network.objects.get(pk=seed["network_1"])


@pytest.fixture
def network_2(seed, db):
    return Network.objects.get(pk=seed["network_2"])


@pytest.fixture
def equipment(seed, db):
    return {
        "manufacturer": Manufacturer.objects.get(pk=seed["manufacturer"]),
        "receiver": Receiver.objects.get(pk=seed["receiver"]),
        "antenna": Antenna.objects.get(pk=seed["antenna"]),
        "radome": Radome.objects.get(pk=seed["radome"]),
    }


def _user(pk):
    return get_user_model().objects.get(pk=pk)


@pytest.fixture
def editor(seed, db):
    return _user(seed["editor"])


@pytest.fixture
def moderator(seed, db):
    return _user(seed["moderator"])


@pytest.fixture
def other_editor(seed, db):
    return _user(seed["other_editor"])


@pytest.fixture
def superuser(seed, db):
    return _user(seed["superuser"])


@pytest.fixture
def api_client():
    """Factory: ``api_client(user)`` returns a logged in DRF client."""
    return logged_in_client


###############################################################################
# Signals


class SignalRecorder:
    """Records every SLM signal sent while the fixture is active."""

    def __init__(self):
        self.received = []

    def __call__(self, sender, signal, **kwargs):
        self.received.append((signal, kwargs))

    @property
    def signals(self):
        return [sig for sig, _ in self.received]

    def clear(self):
        self.received.clear()


@pytest.fixture
def signals():
    recorder = SignalRecorder()
    connected = [
        sig for _, sig in inspect.getmembers(slm_signals) if isinstance(sig, Signal)
    ]
    for sig in connected:
        sig.connect(recorder, weak=False)
    yield recorder
    for sig in connected:
        sig.disconnect(recorder)


###############################################################################
# Sites


@pytest.fixture
def published_site(seed, db):
    """AAA600USA uploaded by the editor and published by the moderator."""
    return Site.objects.get(pk=seed["published_site"])


@pytest.fixture
def proposed_site(editor, agency_1):
    """A site that has been proposed but has no section data."""
    return create_site(logged_in_client(editor), "AAA100USA", agency_1)


def make_updated(site, editor):
    ident = site.siteidentification_set.head()
    response = logged_in_client(editor).post(
        reverse("slm_edit_api:siteidentification-list"),
        data={
            "site": site.pk,
            "site_name": ident.site_name,
            "iers_domes_number": ident.iers_domes_number,
            "monument_description": ident.monument_description,
            "date_installed": ident.date_installed.isoformat(),
            "monument_height": (ident.monument_height or 0) + 0.1,
        },
        format="json",
        secure=True,
    )
    assert response.status_code < 300, response.content
    site.refresh_from_db()
    assert site.status == SiteLogStatus.UPDATED
    return site


@pytest.fixture
def updated_site(published_site, editor):
    """A published site with one unpublished section edit."""
    return make_updated(published_site, editor)


def _set_status(site, status):
    Site.objects.filter(pk=site.pk).update(status=status)
    site.refresh_from_db()
    return site


@pytest.fixture
def former_site(published_site):
    return _set_status(published_site, SiteLogStatus.FORMER)


@pytest.fixture
def suspended_site(published_site):
    return _set_status(published_site, SiteLogStatus.SUSPENDED)
