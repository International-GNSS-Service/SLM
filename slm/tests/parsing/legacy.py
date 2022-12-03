from unittest import TestCase
from slm.legacy.parser import SiteLogParser
from pathlib import Path


file_dir = Path(__file__).parent / 'files'


class TestLegacyParser(TestCase):

    def test_AAA200USA(self):

        with open(file_dir / 'AAA200USA_20220909.log', 'r') as log:
            content = log.read()

        parsed = SiteLogParser(content)
        for _, finding in parsed.findings.items():
            print(finding)

        print(parsed.graphic)
