from unittest import TestCase

from django.conf import settings

from slm.defines import SiteLogStatus


class TestSiteLogStatus(TestCase):
    def test_equality(self):
        self.assertEqual(SiteLogStatus.FORMER, "Former")
        self.assertEqual(SiteLogStatus.PROPOSED, "PROPOSED")
        self.assertEqual(SiteLogStatus.UPDATED, SiteLogStatus("UPDATED"))
        self.assertEqual(SiteLogStatus.PUBLISHED, "Published")
        self.assertEqual(SiteLogStatus.EMPTY, "EmptY")

        self.assertEqual(SiteLogStatus.PUBLISHED.label, "Published")
        self.assertEqual(SiteLogStatus.FORMER.label, "Former")
        self.assertEqual(SiteLogStatus.PROPOSED.label, "Proposed")
        self.assertEqual(SiteLogStatus.UPDATED.label, "Updated")
        self.assertEqual(SiteLogStatus.EMPTY.label, "Empty")

        self.assertEqual(str(SiteLogStatus.PUBLISHED), "Published")
        self.assertEqual(str(SiteLogStatus.FORMER), "Former")
        self.assertEqual(str(SiteLogStatus.PROPOSED), "Proposed")
        self.assertEqual(str(SiteLogStatus.UPDATED), "Updated")
        self.assertEqual(str(SiteLogStatus.EMPTY), "Empty")

        self.assertEqual(SiteLogStatus.FORMER, 1)
        self.assertEqual(SiteLogStatus.PROPOSED, 2)
        self.assertEqual(SiteLogStatus.UPDATED, 3)
        self.assertEqual(SiteLogStatus.PUBLISHED, 4)
        self.assertEqual(SiteLogStatus.EMPTY, 5)
        self.assertEqual(SiteLogStatus.SUSPENDED, 6)

    def test_merge(self):
        self.assertEqual(
            SiteLogStatus.FORMER.merge(SiteLogStatus.PROPOSED), SiteLogStatus.FORMER
        )
        self.assertEqual(
            SiteLogStatus.SUSPENDED.merge(SiteLogStatus.PROPOSED),
            SiteLogStatus.PROPOSED,
        )
        self.assertEqual(
            SiteLogStatus.PROPOSED.merge(SiteLogStatus.FORMER), SiteLogStatus.FORMER
        )
        self.assertEqual(
            SiteLogStatus.PROPOSED.merge(SiteLogStatus.SUSPENDED),
            SiteLogStatus.PROPOSED,
        )

        self.assertEqual(
            SiteLogStatus.FORMER.merge(SiteLogStatus.PUBLISHED), SiteLogStatus.FORMER
        )
        self.assertEqual(
            SiteLogStatus.PUBLISHED.merge(SiteLogStatus.FORMER), SiteLogStatus.FORMER
        )

        self.assertEqual(
            SiteLogStatus.PUBLISHED.merge(SiteLogStatus.UPDATED), SiteLogStatus.UPDATED
        )
        self.assertEqual(
            SiteLogStatus.UPDATED.merge(SiteLogStatus.PUBLISHED), SiteLogStatus.UPDATED
        )

        self.assertEqual(
            SiteLogStatus.PROPOSED.merge(SiteLogStatus.UPDATED), SiteLogStatus.PROPOSED
        )
        self.assertEqual(
            SiteLogStatus.UPDATED.merge(SiteLogStatus.PROPOSED), SiteLogStatus.PROPOSED
        )

        self.assertEqual(SiteLogStatus.FORMER.merge(None), SiteLogStatus.FORMER)

        self.assertEqual(SiteLogStatus.PROPOSED.merge(None), SiteLogStatus.PROPOSED)
        self.assertEqual(SiteLogStatus.UPDATED.merge(None), SiteLogStatus.UPDATED)
        self.assertEqual(SiteLogStatus.PUBLISHED.merge(None), SiteLogStatus.PUBLISHED)

    def test_colors(self):
        for status in SiteLogStatus:
            self.assertEqual(status.color, settings.SLM_STATUS_COLORS[status])

    def test_css(self):
        for status in SiteLogStatus:
            self.assertEqual(
                status.css, f"slm-status-{status.label.lower().replace(' ', '-')}"
            )
