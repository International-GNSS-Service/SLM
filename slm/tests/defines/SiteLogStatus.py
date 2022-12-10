from unittest import TestCase

from django.conf import settings
from slm.defines import SiteLogStatus


class TestSiteLogStatus(TestCase):

    def test_equality(self):

        self.assertEqual(SiteLogStatus.DORMANT, 'Dormant')
        self.assertEqual(SiteLogStatus.PENDING, 'PENDING')
        self.assertEqual(SiteLogStatus.UPDATED, SiteLogStatus('UPDATED'))
        self.assertEqual(SiteLogStatus.PUBLISHED, 'Published')

        self.assertEqual(SiteLogStatus.PUBLISHED.label, 'Published')
        self.assertEqual(SiteLogStatus.DORMANT.label, 'Dormant')
        self.assertEqual(SiteLogStatus.PENDING.label, 'Pending')
        self.assertEqual(SiteLogStatus.UPDATED.label, 'Updated')

        self.assertEqual(str(SiteLogStatus.PUBLISHED), 'Published')
        self.assertEqual(str(SiteLogStatus.DORMANT), 'Dormant')
        self.assertEqual(str(SiteLogStatus.PENDING), 'Pending')
        self.assertEqual(str(SiteLogStatus.UPDATED), 'Updated')

        self.assertEqual(SiteLogStatus.DORMANT, 0)
        self.assertEqual(SiteLogStatus.PENDING, 1)
        self.assertEqual(SiteLogStatus.UPDATED, 2)
        self.assertEqual(SiteLogStatus.PUBLISHED, 3)

    def test_merge(self):

        self.assertEqual(
            SiteLogStatus.DORMANT.merge(SiteLogStatus.PENDING),
            SiteLogStatus.DORMANT
        )
        self.assertEqual(
            SiteLogStatus.PENDING.merge(SiteLogStatus.DORMANT),
            SiteLogStatus.DORMANT
        )

        self.assertEqual(
            SiteLogStatus.DORMANT.merge(SiteLogStatus.PUBLISHED),
            SiteLogStatus.DORMANT
        )
        self.assertEqual(
            SiteLogStatus.PUBLISHED.merge(SiteLogStatus.DORMANT),
            SiteLogStatus.DORMANT
        )

        self.assertEqual(
            SiteLogStatus.PUBLISHED.merge(SiteLogStatus.UPDATED),
            SiteLogStatus.UPDATED
        )
        self.assertEqual(
            SiteLogStatus.UPDATED.merge(SiteLogStatus.PUBLISHED),
            SiteLogStatus.UPDATED
        )

        self.assertEqual(
            SiteLogStatus.PENDING.merge(SiteLogStatus.UPDATED),
            SiteLogStatus.PENDING
        )
        self.assertEqual(
            SiteLogStatus.UPDATED.merge(SiteLogStatus.PENDING),
            SiteLogStatus.PENDING
        )

        self.assertEqual(
            SiteLogStatus.DORMANT.merge(None),
            SiteLogStatus.DORMANT
        )

        self.assertEqual(
            SiteLogStatus.PENDING.merge(None),
            SiteLogStatus.PENDING
        )
        self.assertEqual(
            SiteLogStatus.UPDATED.merge(None),
            SiteLogStatus.UPDATED
        )
        self.assertEqual(
            SiteLogStatus.PUBLISHED.merge(None),
            SiteLogStatus.PUBLISHED
        )

    def test_colors(self):

        for status in SiteLogStatus:
            self.assertEqual(
                status.color,
                settings.SLM_STATUS_COLORS[status]
            )

    def test_css(self):

        for status in SiteLogStatus:
            self.assertEqual(
                status.css,
                f'slm-status-{status.label.lower()}'
            )
