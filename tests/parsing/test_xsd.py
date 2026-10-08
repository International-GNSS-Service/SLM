from datetime import date, datetime
from unittest import TestCase

from slm.parsing.xsd.binding import SiteLogBinder
from slm.parsing.xsd.parser import Error, SiteLogParser
from tests.resources import GML_04, GML_05


class TestXSDParser(TestCase):
    ex_04 = ""
    ex_05 = ""

    expected = {
        (0, None, None): {
            "date_prepared": date(year=2016, month=10, day=27),
            "prepared_by": "Amy Peterson",
            "report_type": "UPDATE",
        }
    }

    def setUp(self):
        self.ex_04 = GML_04.read_text()

        self.ex_05 = GML_05.read_text()

    def test_0_4(self):
        parsed = SiteLogParser(self.ex_04)
        SiteLogBinder(parsed)
        for section_heading, section in parsed.sections.items():
            self.assertDictEqual(
                self.expected.get(section_heading, {}), section.binding
            )

    def test_0_5(self):
        parsed = SiteLogParser(self.ex_05)
        SiteLogBinder(parsed)
        for section_heading, section in parsed.sections.items():
            self.assertDictEqual(
                self.expected.get(section_heading, {}), section.binding
            )

    """
    def test_name_match(self):

        parsed = SiteLogParser(self.AAA200USA, site_name='AAA200USA')
        self.assertTrue(parsed.name_matched)
        self.assertEqual('AAA200USA', parsed.site_name)
        self.assertEqual(parsed.findings.get(0, None), None)

        parsed = SiteLogParser(self.AAA200USA, site_name=None)
        self.assertEqual('AAA200USA', parsed.site_name)
        self.assertEqual(parsed.findings.get(0, None), None)

        parsed = SiteLogParser(self.AAA200USA, site_name='AAA300USA')
        self.assertFalse(parsed.name_matched)
        self.assertEqual('AAA200USA', parsed.site_name)
        self.assertIsInstance(parsed.findings[0], Error)
    """
