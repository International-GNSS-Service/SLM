"""Paths to the static data files used by the test suite."""

from pathlib import Path

FILES = Path(__file__).parent / "files"

LEGACY = FILES / "legacy"
GML = FILES / "gml"
IMAGES = FILES / "images"
EQUIPMENT = FILES / "equipment"
ARCHIVE = FILES / "archive"

AAA200USA_LOG = LEGACY / "AAA200USA_20220909.log"
AAA600USA_LOG = LEGACY / "AAA600USA_20240418.log"
MALFORMED_LOG = LEGACY / "malformed.log"

GML_04 = GML / "0.4" / "20na_20161027.xml"
GML_05 = GML / "0.5" / "20na_20161027.xml"

JPLM_JPG = IMAGES / "jplm.jpg"
ATTACHMENT_PDF = FILES / "attachment.pdf"

# header + two satellites + JAV_GRANT-G3T NONE from igs20.atx
ANTEX_EXCERPT = EQUIPMENT / "igs20_excerpt.atx.gz"
