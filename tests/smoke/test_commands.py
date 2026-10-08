"""
Smoke tests for the SLM management commands. Each command is run against the
seeded fixture data and must complete without error.

``update_data_availability`` is not covered - it requires an FTP server.
"""

import json
from io import StringIO

import pytest
from django.core.management import call_command

from slm.defines import SiteLogStatus
from slm.models import (
    Antenna,
    ArchiveIndex,
    Manufacturer,
    Radome,
    Receiver,
    Site,
)
from tests.resources import ANTEX_EXCERPT, ARCHIVE, EQUIPMENT, GML_04, GML_05


def run(*args, **kwargs):
    out = StringIO()
    call_command(*args, stdout=out, stderr=out, **kwargs)
    return out.getvalue()


def test_validate_db(published_site):
    run("validate_db")
    run("validate_db", published_site.name, "--clear")
    run("validate_db", "--all")


@pytest.mark.parametrize("gml", [GML_04, GML_05], ids=["0.4", "0.5"])
def test_validate_gml(db, gml):
    run("validate_gml", str(gml))


def test_synchronize(published_site):
    run("synchronize")
    run("synchronize", published_site.name)
    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.PUBLISHED


def test_build_index(published_site):
    assert ArchiveIndex.objects.filter(site=published_site).exists()
    run("build_index")
    assert ArchiveIndex.objects.filter(site=published_site).exists()


def test_head_from_index(published_site, tmp_path):
    run(
        "head_from_index",
        published_site.name,
        "--no-prompt",
        "--logs",
        str(tmp_path),
        verbosity=0,
    )
    published_site.refresh_from_db()
    assert published_site.siteidentification_set.head() is not None


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="BUG: with verbosity > 0 (the default) handle() returns the log index "
    "Path, and Django's execute() crashes calling .endswith() on it.",
)
def test_head_from_index_default_verbosity(published_site, tmp_path):
    run("head_from_index", published_site.name, "--no-prompt", "--logs", str(tmp_path))


class FakeStream:
    """Stand-in for a streamed requests response."""

    def __init__(self, path, content_type="application/x-gzip"):
        self.data = path.read_bytes()
        self.status_code = 200
        self.reason = "OK"
        self.headers = {"content-type": content_type}

    def iter_content(self, chunk_size=4096):
        for idx in range(0, len(self.data), chunk_size):
            yield self.data[idx : idx + chunk_size]
        yield b""


@pytest.fixture
def antex(monkeypatch):
    monkeypatch.setattr(
        "slm.management.commands.generate_sinex.requests.get",
        lambda url, **_: FakeStream(ANTEX_EXCERPT),
    )


def _sinex(tmp_path, *args):
    destination = tmp_path / "slm.snx"
    run("generate_sinex", str(destination), *args)
    return destination.read_text()


def test_generate_sinex(published_site, tmp_path, antex):
    sinex = _sinex(tmp_path)
    assert sinex.startswith("%=SNX")
    assert sinex.rstrip().endswith("%ENDSNX")
    code = published_site.name[:4].lower()
    for block in ("SITE/ID", "SITE/RECEIVER", "SITE/ANTENNA", "SITE/ECCENTRICITY"):
        body = sinex.split(f"+{block}")[1].split(f"-{block}")[0]
        assert f" {code} " in body, block
    assert "JAVAD TRE_3 DELTA" in sinex


def test_generate_sinex_former(published_site, proposed_site, tmp_path, antex):
    code = published_site.name[:4].lower()
    Site.objects.filter(pk=published_site.pk).update(status=SiteLogStatus.FORMER)
    assert f" {code} " not in _sinex(tmp_path)
    included = _sinex(tmp_path, "--include-former")
    assert f" {code} " in included
    # proposed sites are never included
    assert f" {proposed_site.name[:4].lower()} " not in included


@pytest.mark.parametrize("fmt", ["legacy", "xml"])
def test_sitelog(published_site, fmt):
    out = run("sitelog", published_site.name, fmt)
    assert published_site.name[:4] in out.upper()


def test_sitelog_head(updated_site):
    head = updated_site.siteidentification_set.head()
    out = run("sitelog", "--head", updated_site.name, "legacy")
    assert f"{head.monument_height:.1f}" in out


def test_set_site(db, settings):
    from django.contrib.sites.models import Site as DjangoSite

    run("set_site")
    assert DjangoSite.objects.filter(pk=settings.SITE_ID).exists()


def test_check_upgrade(db):
    run("check_upgrade", "is-safe")


###############################################################################
# import_equipment - served from local JSON instead of the network


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


@pytest.fixture
def equipment_source(monkeypatch):
    requested = []

    def fake_get(url, *args, **kwargs):
        requested.append(url)
        endpoint = url.rstrip("/").split("/")[-1]
        return FakeResponse(json.loads((EQUIPMENT / f"{endpoint}.json").read_text()))

    monkeypatch.setattr(
        "slm.management.commands.import_equipment.requests.get", fake_get
    )
    return requested


def test_import_equipment(db, equipment_source):
    run("import_equipment")
    assert {"manufacturer", "antenna", "receiver", "radome"} <= {
        url.rstrip("/").split("/")[-1] for url in equipment_source
    }
    assert Manufacturer.objects.filter(name="TRIMBLE").exists()
    assert Antenna.objects.filter(model="TRM59800.00").exists()
    assert Receiver.objects.filter(model="TRIMBLE ALLOY").exists()
    assert Radome.objects.filter(model="JVDM").exists()


def test_import_equipment_remove(published_site, equipment_source):
    Receiver.objects.create(model="OBSOLETE RX")
    run("import_equipment", "--remove")
    assert not Receiver.objects.filter(model="OBSOLETE RX").exists()
    assert Receiver.objects.filter(model="JAVAD TRE_3 DELTA").exists()


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="BUG: invoking a subcommand (e.g. `import_equipment receivers`) returns "
    "the chained results list from handle(), and Django's execute() crashes "
    "calling .endswith() on it.",
)
def test_import_equipment_subcommand(db, equipment_source):
    run("import_equipment", "receivers")


###############################################################################
# import_archive


def test_import_archive(agency_1, equipment, tmp_path):
    run(
        "import_archive",
        str(ARCHIVE),
        "--agency",
        agency_1.shortname,
        "--logs",
        str(tmp_path),
        verbosity=0,
    )
    for name in ("AAA200USA", "AAA600USA"):
        site = Site.objects.get(name=name)
        assert ArchiveIndex.objects.filter(site=site).exists()
        assert agency_1 in site.agencies.all()


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="BUG: with verbosity > 0 (the default) handle() returns the log index "
    "Path, and Django's execute() crashes calling .endswith() on it.",
)
def test_import_archive_default_verbosity(db, tmp_path):
    run("import_archive", str(ARCHIVE), "--logs", str(tmp_path))


def test_import_archive_no_create(db, tmp_path):
    run(
        "import_archive",
        str(ARCHIVE),
        "--no-create-sites",
        "--logs",
        str(tmp_path),
        verbosity=0,
    )
    assert not Site.objects.filter(name="AAA200USA").exists()
