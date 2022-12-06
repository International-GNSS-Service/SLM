from unittest import TestCase
from slm.legacy.parser import SiteLogParser, Error
from slm.legacy.binding import SiteLogBinder
from pathlib import Path


file_dir = Path(__file__).parent / 'files'


class TestLegacyParser(TestCase):

    AAA200USA = ''

    def setUp(self):
        with open(file_dir / 'AAA200USA_20220909.log', 'r') as log:
            self.AAA200USA = log.read()

    def test_AAA200USA(self):

        parsed = SiteLogParser(self.AAA200USA)
        print()
        for _, finding in parsed.findings.items():
            print(finding)

        #print(parsed.graphic)
        from pprint import pprint
        pprint(parsed.sections)

        bound_log = SiteLogBinder(parsed)
        for section_heading, section_data in bound_log.binding.items():
            print(f'################## {section_heading} ##################')
            pprint(section_data)

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
