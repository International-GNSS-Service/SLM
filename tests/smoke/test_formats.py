"""
Round trip smoke tests: a site log uploaded into the database and rendered
back out should carry the same information.
"""

import pytest

from slm.api.serializers import SiteLogSerializer
from slm.defines import SiteLogFormat
from slm.parsing.legacy.binding import SiteLogBinder as LegacyBinder
from slm.parsing.legacy.parser import SiteLogParser as LegacyParser
from slm.parsing.xsd.binding import SiteLogBinder as XSDBinder
from slm.parsing.xsd.parser import SiteLogParser as XSDParser
from tests.resources import AAA600USA_LOG

# section 0 (the form section) legitimately changes on every render
IGNORED_SECTIONS = {0}


def legacy_bindings(text, site_name):
    parsed = LegacyParser(text, site_name=site_name)
    LegacyBinder(parsed)
    return {
        heading: section.binding
        for heading, section in parsed.sections.items()
        if section.binding and heading[0] not in IGNORED_SECTIONS
    }


@pytest.mark.parametrize("fmt", [SiteLogFormat.LEGACY, SiteLogFormat.ASCII_9CHAR])
def test_legacy_round_trip(published_site, fmt):
    original = legacy_bindings(AAA600USA_LOG.read_text(), published_site.name)
    rendered = SiteLogSerializer(instance=published_site).format(fmt)
    round_tripped = legacy_bindings(rendered, published_site.name)

    assert set(round_tripped) == set(original)
    for heading, binding in original.items():
        assert round_tripped[heading] == binding, heading


def test_legacy_render_parses_cleanly(published_site):
    rendered = SiteLogSerializer(instance=published_site).format(SiteLogFormat.LEGACY)
    parsed = LegacyParser(rendered, site_name=published_site.name)
    errors = {line: str(f) for line, f in parsed.findings.items() if f.level == "E"}
    assert not errors


def test_geodesyml_render_parses(published_site):
    rendered = SiteLogSerializer(instance=published_site).format(
        SiteLogFormat.GEODESY_ML
    )
    parsed = XSDParser(rendered, site_name=published_site.name)
    XSDBinder(parsed)
    assert parsed.sections


def test_unpublished_render_includes_edits(updated_site):
    head = updated_site.siteidentification_set.head()
    rendered = SiteLogSerializer(instance=updated_site, published=None).format(
        SiteLogFormat.LEGACY
    )
    bindings = legacy_bindings(rendered, updated_site.name)
    assert bindings[(1, None, None)]["monument_height"] == pytest.approx(
        head.monument_height
    )

    published = SiteLogSerializer(instance=updated_site).format(SiteLogFormat.LEGACY)
    assert legacy_bindings(published, updated_site.name)[(1, None, None)].get(
        "monument_height"
    ) != pytest.approx(head.monument_height)
