from pathlib import Path
from unittest import TestCase

from slm.parsing.legacy.binding import SiteLogBinder
from slm.parsing.legacy.parser import Error, SiteLogParser

file_dir = Path(__file__).parent / "files"


class TestLegacyParser(TestCase):
    AAA200USA = ""

    def setUp(self):
        with open(file_dir / "AAA200USA_20220909.log", "r") as log:
            self.AAA200USA = log.read()

    def test_AAA200USA(self):
        parsed = SiteLogParser(self.AAA200USA)
        for _, finding in parsed.findings.items():
            print(finding)

        # print(parsed.graphic)
        # from pprint import pprint
        # pprint(parsed.sections)

        SiteLogBinder(parsed)
        # for section_heading, section in parsed.sections.items():
        #    print(f'################## {section_heading} ##################')
        #    print(section_heading)
        #    for name, parameter in section.binding.items():
        #        print(f'{name} = {parameter}')

    def test_name_match(self):
        parsed = SiteLogParser(self.AAA200USA, site_name="AAA200USA")
        self.assertTrue(parsed.name_matched)
        self.assertEqual("AAA200USA", parsed.site_name)
        self.assertEqual(parsed.findings.get(0, None), None)

        parsed = SiteLogParser(self.AAA200USA, site_name=None)
        self.assertEqual("AAA200USA", parsed.site_name)
        self.assertEqual(parsed.findings.get(0, None), None)

        parsed = SiteLogParser(self.AAA200USA, site_name="AAA300USA")
        self.assertFalse(parsed.name_matched)
        self.assertEqual("AAA200USA", parsed.site_name)
        self.assertIsInstance(parsed.findings[0], Error)
