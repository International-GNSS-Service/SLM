"""
Used to testing application.

NOTES: Currently unused but can be useful
for testing various functionalities.

Run
$ python3 manage.py test
to run tests

More info:
https://docs.djangoproject.com/en/3.2/topics/testing/overview/
"""

import inspect

from django.contrib.auth import get_user_model
from django.dispatch import Signal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

import json

from slm import signals as slm_signals
from slm.api.edit import views as edit_views
from slm.defines import SiteLogStatus, EquipmentState
from slm.models import Agency, Network, Site, Radome, Antenna, Receiver
from tests.defines.ISOCountry import TestISOCountry  # dont remove
from tests.defines.SiteLogStatus import TestSiteLogStatus  # dont remove
from tests.parsing.legacy import TestLegacyParser  # dont remove
from tests.parsing.xsd import TestXSDParser  # dont remove


class ReceivedSignal:
    @property
    def name(self):
        for name, sig in inspect.getmembers(slm_signals):
            if isinstance(sig, Signal):
                if self.signal is sig:
                    return name
        return None

    def __init__(self, signal, kwargs):
        self.signal = signal
        self.kwargs = kwargs


NON_SECTION_FIELDS = {
    "_flags",
    "_diff",
    "can_publish",
    "published",
    "id",
    "is_deleted",
    "subsection",
}


def normalize(serialized):
    return {key: val if val is not None else "" for key, val in serialized.items()}


def strip_meta(serialized):
    return {
        key: val for key, val in serialized.items() if key not in NON_SECTION_FIELDS
    }


def serialize(instance, strip=True):
    """
    Serialize a section instance using its edit serializer.

    :param instance: The instance to serializer
    :param strip: If true (default) strip out non-section fields that are
        part of editing metadata.
    :return: A serialized dictionary representing the instance
    """
    for name, view in inspect.getmembers(edit_views):
        if (
            type(view) is edit_views.SectionViewSet
            and view.serializer_class.Meta.model is instance.__class__
        ):
            if strip:
                return normalize(strip_meta(view.serializer_class(instance).data))
            return normalize(view.serializer_class(instance).data)
    return None


class SLMSignalTracker:
    signals = []

    def clear_signals(self):
        self.signals = []

    def handle_signal(self, sender, **kwargs):
        self.signals.append(ReceivedSignal(kwargs.pop("signal"), kwargs))

    def setUp(self):
        for name, signal in inspect.getmembers(slm_signals):
            if isinstance(signal, Signal):
                signal.connect(self.handle_signal)


class TestEditAPI(SLMSignalTracker, TestCase):
    test_agency_1 = None
    test_agency_2 = None

    test_network_1 = None
    test_network_2 = None

    test_editor = None
    test_moderator = None
    test_superuser = None

    receiver = None
    antenna = None
    radome = None

    def setUp(self):
        self.clear_signals()
        self.test_agency_1 = Agency.objects.create(name="Test Agency 1")
        self.test_agency_2 = Agency.objects.create(name="Test Agency 2")

        self.test_network_1 = Network.objects.create(name="Test Network 1")
        self.test_network_2 = Network.objects.create(name="Test Network 2")

        self.test_editor = get_user_model().objects.create_user(
            email="editor@example.com",
            password="password",
            first_name="Test",
            last_name="Editor",
        )
        self.test_editor.agencies.add(self.test_agency_1)

        self.test_moderator = get_user_model().objects.create_user(
            email="moderator@example.com",
            password="password",
            first_name="Test",
            last_name="Moderator",
        )
        self.test_moderator.agencies.add(self.test_agency_1)

        self.test_superuser = get_user_model().objects.create_superuser(
            email="superuser@example.com",
            password="password",
            first_name="Test",
            last_name="Superuser",
        )

        # set up equipment
        self.receiver = Receiver.objects.create(
            model="JAVAD TRE_3 DELTA", state=EquipmentState.ACTIVE
        )
        self.antenna = Antenna.objects.create(
            model="JAV_GRANT-G3T", state=EquipmentState.ACTIVE
        )
        self.radome = Radome.objects.create(model="JVDM", state=EquipmentState.ACTIVE)
        super().setUp()

    def test_propose(self):
        self.clear_signals()

        c = APIClient()
        self.assertTrue(c.login(email="editor@example.com", password="password"))

        ret = c.post(
            reverse("slm_edit_api:stations-list"),
            data={"name": "AAA200USA", "agencies": [{"id": self.test_agency_1.id}]},
            follow=True,
            format="json",
            secure=True,
        )
        self.assertEqual(ret.status_code, 403)

        self.assertTrue(c.login(email="superuser@example.com", password="password"))

        ret = c.post(
            reverse("slm_edit_api:stations-list"),
            {"name": "AAA200USA", "agencies": [{"id": self.test_agency_1.id}]},
            follow=True,
            format="json",
            secure=True,
        )
        self.assertTrue(ret.status_code < 300)

        self.assertEqual(
            Site.objects.get(name="AAA200USA").status, SiteLogStatus.PROPOSED
        )

        self.assertEqual(
            Site.objects.get(name="AAA200USA").agencies.first(), self.test_agency_1
        )

        self.assertEqual(Site.objects.get(name="AAA200USA").agencies.count(), 1)

        self.assertEqual(len(self.signals), 2)
        self.assertEqual(self.signals[0].signal, slm_signals.site_status_changed)
        self.assertEqual(self.signals[1].signal, slm_signals.site_proposed)

    def test_nominal_workflow(self):
        self.clear_signals()
        Site.objects.all().delete()
        site = Site.objects.create(name="AAA200USA")
        site.agencies.add(self.test_agency_1)

        c = APIClient()
        self.assertTrue(c.login(email="editor@example.com", password="password"))

        ident = {
            "site": site.id,
            "site_name": "Astronomical Observatory of INASAN",
            "monument_inscription": "Stable pillar on the roof of the main building",
            "iers_domes_number": "12330M001",
            "cdp_number": "",
            "date_installed": "1995-03-08T00:00:00Z",
            "monument_description": "PILLAR",
            "monument_height": 0.5,
            "monument_foundation": "ROOF",
            "foundation_depth": "",
            "marker_description": "BRASS NAIL",
            "geologic_characteristic": "",
            "bedrock_type": "",
            "bedrock_condition": "",
            "fracture_spacing": "",
            "fault_zones": "",
            "distance": "",
            "additional_information": "",
        }
        location = {
            "site": site.id,
            "city": "Ny-Alesund",
            "state": "Svalbard",
            "country": "NO",
            "tectonic": "EU",
            "xyz": [1202431.0, 252627.0, 6237768.0],
            "llh": [78.9295809046, 11.8650953117, 78.99],
            "additional_information": "",
        }

        # CREATE
        ret = c.post(
            reverse("slm_edit_api:siteidentification-list"),
            data=ident,
            follow=True,
            secure=True,
            format="json",
        )
        site.refresh_from_db()

        self.assertTrue(ret.status_code < 300)

        self.assertEqual(site.status, SiteLogStatus.PROPOSED)

        self.assertEqual(len(self.signals), 2)

        self.assertEqual(self.signals[0].signal, slm_signals.site_status_changed)
        self.assertEqual(self.signals[1].signal, slm_signals.section_added)

        # should only be one unpublished row
        self.assertTrue(site.siteidentification_set.count(), 1)

        edited = serialize(site.siteidentification_set.first())

        self.assertDictEqual(ident, edited)

        self.clear_signals()

        # edit - should still be only one unpublished row
        ident_ret = c.post(
            reverse("slm_edit_api:siteidentification-list"),
            data={
                **edited,
                "monument_height": 0.6,
            },
            follow=True,
            secure=True,
            format="json",
        )
        self.assertTrue(ret.status_code < 300)
        loc_ret = c.post(
            reverse("slm_edit_api:sitelocation-list"),
            data=location,
            follow=True,
            secure=True,
            format="json",
        )

        self.assertTrue(loc_ret.status_code < 300)
        site.refresh_from_db()

        self.assertEqual(site.status, SiteLogStatus.PROPOSED)

        self.assertTrue(site.siteidentification_set.count(), 1)
        self.assertTrue(site.sitelocation_set.count(), 1)

        self.assertDictEqual(
            normalize(strip_meta(ident_ret.json())),
            {
                **edited,
                "monument_height": 0.6,
            },
        )
        self.assertDictEqual(
            normalize(strip_meta(loc_ret.json())),
            location,
        )

        self.assertEqual(len(self.signals), 2)

        self.assertEqual(self.signals[0].signal, slm_signals.section_edited)
        self.assertEqual(self.signals[1].signal, slm_signals.section_added)

        self.clear_signals()

        # publish - should still be only one unpublished row
        ret = c.post(
            reverse("slm_edit_api:siteidentification-list"),
            data={
                **edited,
                "publish": True,
            },
            follow=True,
            secure=True,
            format="json",
        )

        site.refresh_from_db()

        self.assertEqual(site.status, SiteLogStatus.PROPOSED)

        self.assertEqual(ret.status_code, 403)

        self.assertTrue(c.login(email="superuser@example.com", password="password"))

        self.clear_signals()

        # edit and publish simultaneously - should be two published rows
        # site log should still be in PROPOSED state because other sections
        # are not published
        ret = c.post(
            reverse("slm_edit_api:siteidentification-list"),
            data={
                **edited,
                "publish": True,
            },
            follow=True,
            secure=True,
            format="json",
        )
        site.refresh_from_db()
        self.assertEqual(site.status, SiteLogStatus.PROPOSED)

        self.assertTrue(ret.status_code < 300)

        self.assertEqual(len(self.signals), 1)

        self.assertEqual(self.signals[0].signal, slm_signals.section_edited)

        self.assertEqual(
            self.signals[0].kwargs.get("fields", None), ["monument_height"]
        )

        self.assertTrue(site.siteidentification_set.count(), 2)

        sections = {
            "sitereceiver": {
                "site": site.id,
                "receiver_type": "JAVAD TRE_3 DELTA",
                "satellite_system": ["GPS", "GLO", "GAL", "BDS"],
                "serial_number": "JV1234AB5678",
                "firmware": "4.3.00",
                "elevation_cutoff": None,
                "installed": "2023-04-03T00:00:00Z",
                "removed": "2023-11-06T00:00:00Z",
                "temp_stabilized": True,
                "temp_nominal": 24.0,
                "temp_deviation": 5.0,
                "additional_info": "",
                "heading": "JAVAD TRE_3 DELTA",
                "effective": "2023-04-03/2023-11-06",
            },
            "siteantenna": {
                "site": site.id,
                "antenna_type": "JAV_GRANT-G3T",
                "serial_number": "ANT-987654321",
                "reference_point": 1,
                "marker_une": [0.0, 0.0, 0.0],
                "alignment": 1.0,
                "radome_type": "JVDM",
                "radome_serial_number": "",
                "cable_type": "",
                "cable_length": None,
                "installed": "2023-04-03T00:00:00Z",
                "removed": None,
                "additional_information": "",
                "custom_graphic": "",
                "heading": "JAV_GRANT-G3T",
                "effective": "2023-04-03",
            },
            "siteoperationalcontact": {
                "site": site.id,
                "agency": "Test Sites",
                "preferred_abbreviation": "TEST",
                "mailing_address": "",
                "primary_name": "Brian Kohan",
                "primary_phone1": "9196324982",
                "primary_phone2": "",
                "primary_fax": "",
                "primary_email": "bckohan@gmail.com",
                "secondary_name": "",
                "secondary_phone1": "",
                "secondary_phone2": "",
                "secondary_fax": "",
                "secondary_email": "",
                "additional_information": "",
            },
            "siteresponsibleagency": {
                "site": site.id,
                "agency": "Test Sites",
                "preferred_abbreviation": "TEST",
                "mailing_address": "",
                "primary_name": "Brian Kohan",
                "primary_phone1": "5556324982",
                "primary_phone2": "",
                "primary_fax": "",
                "primary_email": "bckohan@ggmail.com",
                "secondary_name": "",
                "secondary_phone1": "",
                "secondary_phone2": "",
                "secondary_fax": "",
                "secondary_email": "",
                "additional_information": "",
            },
            "sitemoreinformation": {
                "site": site.id,
                "published": False,
                "can_publish": True,
                "primary": "JPL",
                "secondary": "BKG",
                "more_info": "",
                "sitemap": "",
                "site_diagram": "",
                "horizon_mask": "",
                "monument_description": "",
                "site_picture": "",
                "additional_information": "",
            },
        }

        for section, data in sections.items():
            ret = c.post(
                reverse(f"slm_edit_api:{section}-list"),
                data=data,
                follow=True,
                secure=True,
                format="json",
            )
            site.refresh_from_db()
            self.assertEqual(site.status, SiteLogStatus.PROPOSED)
            self.assertTrue(ret.status_code < 300)

        self.clear_signals()
        self.assertTrue(c.login(email="editor@example.com", password="password"))

        # publish entire log
        ret = c.patch(
            reverse("slm_edit_api:stations-detail", kwargs={"pk": site.id}),
            data={"publish": True},
            follow=True,
            secure=True,
            format="json",
        )
        self.assertEqual(ret.status_code, 403)

        self.assertTrue(c.login(email="superuser@example.com", password="password"))
        ret = c.patch(
            reverse("slm_edit_api:stations-detail", kwargs={"pk": site.id}),
            data={"publish": True},
            follow=True,
            secure=True,
            format="json",
        )
        self.assertTrue(ret.status_code < 300)

        site.refresh_from_db()
        self.assertEqual(site.status, SiteLogStatus.PUBLISHED)

        self.assertEqual(len(self.signals), 3)

        self.assertEqual(self.signals[0].signal, slm_signals.site_status_changed)
        self.assertEqual(self.signals[1].signal, slm_signals.alert_issued)
        self.assertEqual(self.signals[2].signal, slm_signals.site_published)

        self.clear_signals()

        # make another edit - should be 3 rows - top unpublished and two
        # published
        ret = c.post(
            reverse("slm_edit_api:siteidentification-list"),
            data={**edited, "foundation_depth": 2},
            follow=True,
            secure=True,
            format="json",
        )
        site.refresh_from_db()
        self.assertEqual(site.status, SiteLogStatus.UPDATED)
        self.assertTrue(ret.status_code < 300)

        self.assertEqual(len(self.signals), 2)

        self.assertEqual(self.signals[0].signal, slm_signals.section_edited)
        self.assertEqual(self.signals[1].signal, slm_signals.site_status_changed)

        self.assertDictEqual(
            normalize(strip_meta(ret.json())), {**edited, "foundation_depth": 2}
        )

        self.assertDictEqual(
            serialize(site.siteidentification_set.first()),
            {**edited, "foundation_depth": 2},
        )

        self.assertTrue(site.siteidentification_set.count(), 3)

        self.assertEqual(site.status, SiteLogStatus.UPDATED)

        self.clear_signals()
        self.assertTrue(c.login(email="superuser@example.com", password="password"))
        ret = c.patch(
            reverse(
                "slm_edit_api:siteidentification-detail",
                kwargs={"pk": site.siteidentification_set.first().id},
            ),
            data={"publish": True},
            follow=True,
            secure=True,
            format="json",
        )

        self.assertTrue(ret.status_code < 300)
        site.refresh_from_db()
        self.assertEqual(site.status, SiteLogStatus.PUBLISHED)
        self.assertEqual(len(self.signals), 2)

        self.assertTrue(site.siteidentification_set.count(), 3)

        self.assertEqual(self.signals[0].signal, slm_signals.site_published)
        self.assertEqual(self.signals[1].signal, slm_signals.site_status_changed)

        self.clear_signals()

        humidity_sensor = {
            "site": site.id,
            "manufacturer": "Gill Instruments",
            "serial_number": "",
            "height_diff": -0.2,
            "calibration": "",
            "effective_start": "2016-03-17",
            "effective_end": "",
            "notes": "",
            "model": "SCP1000",
            "sampling_interval": 55,
            "accuracy": 3.0,
            "aspiration": "",
            "heading": "SCP1000",
            "effective": "2016-03-17",
        }

        # CREATE SENSOR
        ret = c.post(
            reverse("slm_edit_api:sitehumiditysensor-list"),
            data=humidity_sensor,
            follow=True,
            secure=True,
            format="json",
        )
        subsection = ret.json()["subsection"]
        self.assertTrue(ret.status_code < 300)
        site.refresh_from_db()

        self.assertEqual(len(self.signals), 2)

        self.assertTrue(site.sitehumiditysensor_set.count(), 1)

        self.assertDictEqual(
            humidity_sensor, serialize(site.sitehumiditysensor_set.first())
        )

        self.assertEqual(self.signals[0].signal, slm_signals.section_added)
        self.assertEqual(self.signals[1].signal, slm_signals.site_status_changed)

        self.assertEqual(site.status, SiteLogStatus.UPDATED)

        # PUBLISH SENSOR
        self.clear_signals()
        ret = c.post(
            reverse("slm_edit_api:sitehumiditysensor-list"),
            data={
                **humidity_sensor,
                "subsection": 0,
                "height_diff": -0.3,
                "publish": True,
            },
            follow=True,
            secure=True,
            format="json",
        )
        self.assertTrue(ret.status_code < 300)
        site.refresh_from_db()

        self.assertEqual(len(self.signals), 3)

        self.assertTrue(site.sitehumiditysensor_set.count(), 1)

        self.assertDictEqual(
            {**humidity_sensor, "height_diff": -0.3},
            serialize(site.sitehumiditysensor_set.first()),
        )

        self.assertEqual(self.signals[0].signal, slm_signals.section_edited)
        self.assertEqual(self.signals[1].signal, slm_signals.site_published)
        self.assertEqual(self.signals[2].signal, slm_signals.site_status_changed)

        self.assertEqual(site.status, SiteLogStatus.PUBLISHED)
