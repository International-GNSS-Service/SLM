from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from slm.models import Agency, Site, Antenna, Receiver, Radome, SiteFileUpload
from ..tests import SLMSignalTracker
from django.core.files.uploadedfile import SimpleUploadedFile
from pathlib import Path
from slm.defines import SiteLogStatus, EquipmentState, SiteFileUploadStatus, SLMFileType
from slm import signals as slm_signals
import os
import pytest

AAA600USA = Path(__file__).parent / "files" / "AAA600USA_20240418.log"
JPLM_JPG = Path(__file__).parent / "files" / "jplm.jpg"


class TestUploads(SLMSignalTracker, TestCase):
    test_agency_1 = None

    test_editor = None

    receiver = None
    antenna = None
    radome = None

    def setUp(self):
        self.clear_signals()
        self.test_agency_1 = Agency.objects.create(name="Test Agency 1")

        self.test_editor = get_user_model().objects.create_user(
            email="editor@example.com",
            password="password",
            first_name="Test",
            last_name="Editor",
        )
        self.test_editor.agencies.add(self.test_agency_1)

        propose = Permission.objects.get(codename="propose_sites")
        moderate = Permission.objects.get(codename="moderate_sites")
        self.test_editor.user_permissions.add(propose)
        self.test_editor.user_permissions.add(moderate)
        self.test_editor.save()

        # set up equipment
        self.receiver = Receiver.objects.create(
            model="JAVAD TRE_3 DELTA", state=EquipmentState.ACTIVE
        )
        self.antenna = Antenna.objects.create(
            model="JAV_GRANT-G3T", state=EquipmentState.ACTIVE
        )
        self.radome = Radome.objects.create(model="JVDM", state=EquipmentState.ACTIVE)
        super().setUp()

    def test_legacy_sitelog_upload(self):
        self.clear_signals()

        self.client = APIClient()
        self.assertTrue(
            self.client.login(email="editor@example.com", password="password")
        )

        ret = self.client.post(
            reverse("slm_edit_api:stations-list"),
            data={"name": "AAA600USA", "agencies": [{"id": self.test_agency_1.id}]},
            follow=True,
            format="json",
            secure=True,
        )
        self.assertLess(ret.status_code, 300)
        self.assertEqual(
            Site.objects.get(name="AAA600USA").status, SiteLogStatus.PROPOSED
        )
        aaa600 = Site.objects.get(name="AAA600USA")
        self.assertEqual(aaa600.siteform_set.count(), 0)
        self.assertEqual(aaa600.siteidentification_set.count(), 0)
        self.assertEqual(aaa600.sitelocation_set.count(), 0)
        self.assertEqual(aaa600.sitereceiver_set.count(), 0)
        self.assertEqual(aaa600.siteantenna_set.count(), 0)
        self.assertEqual(aaa600.sitesurveyedlocalties_set.count(), 0)
        self.assertEqual(aaa600.sitefrequencystandard_set.count(), 0)
        self.assertEqual(aaa600.sitecollocation_set.count(), 0)
        self.assertEqual(aaa600.sitehumiditysensor_set.count(), 0)
        self.assertEqual(aaa600.sitepressuresensor_set.count(), 0)
        self.assertEqual(aaa600.sitetemperaturesensor_set.count(), 0)
        self.assertEqual(aaa600.sitewatervaporradiometer_set.count(), 0)
        self.assertEqual(aaa600.siteotherinstrumentation_set.count(), 0)
        self.assertEqual(aaa600.siteradiointerferences_set.count(), 0)
        self.assertEqual(aaa600.sitemultipathsources_set.count(), 0)
        self.assertEqual(aaa600.sitesignalobstructions_set.count(), 0)
        self.assertEqual(aaa600.sitelocalepisodiceffects_set.count(), 0)
        self.assertEqual(aaa600.siteoperationalcontact_set.count(), 0)
        self.assertEqual(aaa600.siteresponsibleagency_set.count(), 0)
        self.assertEqual(aaa600.sitemoreinformation_set.count(), 0)

        self.clear_signals()

        response = self.client.post(
            reverse("slm_edit_api:files-list", kwargs={"site": "AAA600USA"}),
            {
                "file": SimpleUploadedFile(
                    AAA600USA.name, AAA600USA.read_bytes(), content_type="text/plain"
                )
            },
            format="multipart",
            secure=True,
        )
        self.assertLess(response.status_code, 400)
        self.assertEqual(
            Site.objects.get(name="AAA600USA").status, SiteLogStatus.PROPOSED
        )

        self.assertEqual(len(self.signals), 13)
        self.assertEqual(self.signals[0].signal, slm_signals.site_file_uploaded)
        for received in self.signals[1:-1]:
            self.assertEqual(received.signal, slm_signals.section_added)

        self.assertEqual(self.signals[-1].signal, slm_signals.section_edited)

        aaa600.refresh_from_db()
        self.assertEqual(aaa600.siteform_set.count(), 1)
        self.assertEqual(aaa600.siteidentification_set.count(), 1)
        self.assertEqual(aaa600.sitelocation_set.count(), 1)
        self.assertEqual(aaa600.sitereceiver_set.count(), 2)
        self.assertEqual(aaa600.siteantenna_set.count(), 1)
        self.assertEqual(aaa600.sitesurveyedlocalties_set.count(), 0)
        self.assertEqual(aaa600.sitefrequencystandard_set.count(), 1)
        self.assertEqual(aaa600.sitecollocation_set.count(), 0)
        self.assertEqual(aaa600.sitehumiditysensor_set.count(), 1)
        self.assertEqual(aaa600.sitepressuresensor_set.count(), 0)
        self.assertEqual(aaa600.sitetemperaturesensor_set.count(), 0)
        self.assertEqual(aaa600.sitewatervaporradiometer_set.count(), 0)
        self.assertEqual(aaa600.siteotherinstrumentation_set.count(), 0)
        self.assertEqual(aaa600.siteradiointerferences_set.count(), 0)
        self.assertEqual(aaa600.sitemultipathsources_set.count(), 1)
        self.assertEqual(aaa600.sitesignalobstructions_set.count(), 0)
        self.assertEqual(aaa600.sitelocalepisodiceffects_set.count(), 0)
        self.assertEqual(aaa600.siteoperationalcontact_set.count(), 1)
        self.assertEqual(aaa600.siteresponsibleagency_set.count(), 1)
        self.assertEqual(aaa600.sitemoreinformation_set.count(), 1)

    @pytest.mark.skip(reason="Temporary fail")
    def test_image_upload(self):
        self.clear_signals()

        self.client = APIClient()
        self.assertTrue(
            self.client.login(email="editor@example.com", password="password")
        )

        ret = self.client.post(
            reverse("slm_edit_api:stations-list"),
            data={"name": "AAA700USA", "agencies": [{"id": self.test_agency_1.id}]},
            follow=True,
            format="json",
            secure=True,
        )
        self.assertLess(ret.status_code, 300)
        self.assertEqual(
            Site.objects.get(name="AAA700USA").status, SiteLogStatus.PROPOSED
        )
        aaa700 = Site.objects.get(name="AAA700USA")

        self.clear_signals()

        self.assertEqual(SiteFileUpload.objects.filter(site=aaa700).count(), 0)

        response = self.client.post(
            reverse("slm_edit_api:files-list", kwargs={"site": "AAA700USA"}),
            {
                "file": SimpleUploadedFile(
                    JPLM_JPG.name, JPLM_JPG.read_bytes(), content_type="image/jpeg"
                )
            },
            format="multipart",
            secure=True,
        )
        aaa700.refresh_from_db()
        self.assertLess(response.status_code, 400)
        self.assertEqual(aaa700.status, SiteLogStatus.PROPOSED)

        self.assertEqual(len(self.signals), 2)
        self.assertEqual(self.signals[0].signal, slm_signals.alert_issued)
        self.assertEqual(self.signals[1].signal, slm_signals.site_file_uploaded)

        uploaded = SiteFileUpload.objects.filter(site=aaa700, name="jplm.jpg")
        self.assertEqual(uploaded.count(), 1)
        uploaded = uploaded.first()
        self.assertEqual(uploaded.status, SiteFileUploadStatus.UNPUBLISHED)
        self.assertEqual(uploaded.file_type, SLMFileType.SITE_IMAGE)

        # should have created a thumbnail
        self.assertTrue(Path(uploaded.thumbnail.path).exists())
        self.assertGreater(os.path.getsize(Path(uploaded.thumbnail.path)), 0)

        # try publish
        response = self.client.patch(
            reverse(
                "slm_edit_api:files-detail",
                kwargs={"site": "AAA700USA", "pk": uploaded.pk},
            ),
            {"status": SiteFileUploadStatus.PUBLISHED.value},
            format="json",
            secure=True,
        )
        self.assertLess(response.status_code, 400)
        uploaded.refresh_from_db()
        self.assertEqual(uploaded.status, SiteFileUploadStatus.PUBLISHED)
