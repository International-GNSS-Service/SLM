"""
Smoke tests for the public (unauthenticated) API under /api/public/.
"""

import pytest
from django.urls import reverse
from lxml import etree

from slm.parsing.legacy.parser import SiteLogParser as LegacyParser


def rows(response):
    """Return the result rows regardless of which paginator the view uses."""
    data = response.json()
    if isinstance(data, list):
        return data
    if data.get("type") == "FeatureCollection":
        return data["features"]
    for key in ("data", "results"):
        if key in data:
            return data[key]
    raise AssertionError(f"Unrecognized list response: {data}")


def get(client, name, query=None, **kwargs):
    return client.get(reverse(name, kwargs=kwargs), query or {}, secure=True)


LIST_ENDPOINTS = [
    "stations",
    "name",
    "receiver",
    "antenna",
    "radome",
    "manufacturer",
    "files",
    "archive",
    "agency",
    "network",
    "map",
]


@pytest.mark.parametrize("endpoint", LIST_ENDPOINTS)
def test_list_endpoints(api_client, published_site, endpoint):
    response = get(api_client(), f"slm_public_api:{endpoint}-list")
    assert response.status_code == 200, response.content[:2000]
    rows(response)


def test_api_root(api_client, db):
    assert get(api_client(), "slm_public_api:api-root").status_code == 200


def test_stations_list_contains_published(api_client, published_site):
    names = [
        row["name"] for row in rows(get(api_client(), "slm_public_api:stations-list"))
    ]
    assert published_site.name in names


def test_stations_list_excludes_proposed(api_client, published_site, proposed_site):
    names = [
        row["name"] for row in rows(get(api_client(), "slm_public_api:stations-list"))
    ]
    assert proposed_site.name not in names


def test_stations_detail(api_client, published_site):
    response = get(
        api_client(), "slm_public_api:stations-detail", station=published_site.name
    )
    assert response.status_code == 200
    assert response.json()["name"] == published_site.name


def test_stations_search_and_filter(api_client, published_site):
    client = api_client()
    hit = rows(get(client, "slm_public_api:stations-list", {"name": "AAA6"}))
    assert [row["name"] for row in hit] == [published_site.name]
    miss = rows(get(client, "slm_public_api:stations-list", {"name": "ZZZ"}))
    assert miss == []
    searched = rows(get(client, "slm_public_api:stations-list", {"search": "AAA600"}))
    assert [row["name"] for row in searched] == [published_site.name]


def test_stations_filter_by_equipment(api_client, published_site, equipment):
    client = api_client()
    hit = rows(
        get(
            client,
            "slm_public_api:stations-list",
            {"receiver": equipment["receiver"].pk},
        )
    )
    assert published_site.name in [row["name"] for row in hit]


def test_stations_pagination(api_client, published_site):
    response = get(api_client(), "slm_public_api:stations-list", {"limit": 1})
    assert response.status_code == 200
    assert len(rows(response)) <= 1


def test_name_filter(api_client, published_site):
    found = rows(get(api_client(), "slm_public_api:name-list", {"name": "aaa6"}))
    assert [row["name"] for row in found] == [published_site.name]


@pytest.mark.parametrize("endpoint", ["receiver", "antenna", "radome"])
def test_equipment_lists(api_client, equipment, endpoint):
    models = [
        row["model"]
        for row in rows(get(api_client(), f"slm_public_api:{endpoint}-list"))
    ]
    assert equipment[endpoint].model in models


def test_manufacturer_list(api_client, equipment):
    names = [
        row["name"]
        for row in rows(get(api_client(), "slm_public_api:manufacturer-list"))
    ]
    assert equipment["manufacturer"].name in names


def test_agency_and_network_lists(api_client, published_site, agency_1, network_1):
    client = api_client()
    agencies = rows(get(client, "slm_public_api:agency-list"))
    assert agency_1.name in [row["name"] for row in agencies]
    networks = rows(get(client, "slm_public_api:network-list"))
    assert network_1.name in [row["name"] for row in networks]


def test_archive_list_has_published_log(api_client, published_site):
    archive = rows(
        get(api_client(), "slm_public_api:archive-list", {"site": published_site.name})
    )
    assert archive


###############################################################################
# Site log downloads


def download(client, site, fmt, api="public", **query):
    return client.get(
        reverse(f"slm_{api}_api:download-detail", kwargs={"site": site, "format": fmt}),
        query,
        secure=True,
    )


def content(response):
    return (
        b"".join(response.streaming_content) if response.streaming else response.content
    )


@pytest.mark.parametrize("fmt", ["log", "text", "legacy", "sitelog"])
def test_download_legacy(api_client, published_site, fmt):
    response = download(api_client(), published_site.name, fmt)
    assert response.status_code == 200, response.content[:2000]
    text = content(response).decode()
    assert "AAA600USA" in text.upper()
    parsed = LegacyParser(text, site_name=published_site.name)
    assert parsed.name_matched


@pytest.mark.parametrize("fmt", ["xml", "gml"])
def test_download_geodesyml(api_client, published_site, fmt):
    response = download(api_client(), published_site.name, fmt)
    assert response.status_code == 200, response.content[:2000]
    root = etree.fromstring(content(response))
    assert "geodesyml" in root.tag.lower() or root.nsmap


@pytest.mark.xfail(
    strict=True,
    reason="BUG: GeodesyML export emits empty elements for unset numeric sensor "
    "fields (e.g. <geo:dataSamplingInterval/>) which are invalid xs:double values.",
)
def test_download_geodesyml_validates(api_client, published_site):
    from slm.parsing.xsd.parser import SiteLogParser as XSDParser

    response = download(api_client(), published_site.name, "xml")
    parsed = XSDParser(content(response).decode(), site_name=published_site.name)
    errors = [str(f) for f in parsed.findings.values() if f.level == "E"]
    assert not errors, errors


def test_download_lower_case(api_client, published_site):
    response = download(api_client(), published_site.name, "log", lower_case=1)
    assert response.status_code == 200
    assert "aaa600usa_" in response.get("Content-Disposition", "")


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="BUG: the name_len query parameter is passed to Site.get_filename() "
    "as a string and used as a slice index.",
)
def test_download_name_len(api_client, published_site):
    response = download(api_client(), published_site.name, "xml", name_len=4)
    assert response.status_code == 200
    assert "AAA6_" in response.get("Content-Disposition", "")


def test_download_unknown_site(api_client, db):
    assert download(api_client(), "ZZZ000ZZZ", "log").status_code == 404


def test_download_proposed_site_not_public(api_client, published_site, proposed_site):
    assert download(api_client(), proposed_site.name, "log").status_code == 404


def test_public_file_download(api_client, published_site):
    files = rows(get(api_client(), "slm_public_api:files-list"))
    for row in files:
        response = get(api_client(), "slm_public_api:files-detail", pk=row["id"])
        assert response.status_code == 200


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="BUG: get_format_suffix() calls SiteLogFormat(None) when no format "
    "suffix is given, so a bare download URL 500s instead of using a default.",
)
def test_download_without_format_suffix(api_client, published_site):
    response = api_client().get(
        reverse("slm_public_api:download-detail", kwargs={"site": published_site.name}),
        secure=True,
    )
    assert response.status_code == 200
