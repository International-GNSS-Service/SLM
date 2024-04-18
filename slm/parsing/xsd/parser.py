from threading import Lock
from typing import List, Union

from lxml import etree

from slm.defines import GeodesyMLVersion
from slm.parsing import BaseParameter, BaseParser, BaseSection, Error


class Section(BaseSection):
    tree: etree.XML

    def __init__(
        self, tree, parser, section_number, subsection_number=None, order=None
    ):
        self.tree = tree
        super().__init__(
            line_no=tree.sourceline - 1,
            section_number=section_number,
            subsection_number=subsection_number,
            order=order,
            parser=parser,
        )


class Parameter(BaseParameter):
    elements: etree.XML

    def __init__(self, elements, parser, section):
        self.elements = elements
        super().__init__(
            line_no=elements[0].sourceline - 1,
            name=elements[0].tag,
            values=[elem.text for elem in elements],
            parser=parser,
            section=section,
        )
        self.line_end = elements[-1].sourceline - 1


class SiteLogParser(BaseParser):
    """
    Parsing and validation routines for GeodesyML Documents.
    """

    lock = Lock()

    xsd: GeodesyMLVersion
    doc: etree.XML

    def __init__(self, site_log: Union[str, List[str]], site_name: str = None) -> None:
        """

        :param site_log:
        :param site_name:
        """
        super().__init__(site_log=site_log, site_name=site_name)
        try:
            self.doc = etree.fromstring("\n".join(self.lines).encode())

            try:
                self.xsd = GeodesyMLVersion(
                    self.doc.nsmap.get(self.doc.prefix, GeodesyMLVersion.latest())
                )

                # Unclear if schema.validate is thread safe. Serialize access
                # to it to be safe.
                with self.lock:
                    result = self.xsd.schema.validate(self.doc)

                    if not result:
                        for error in self.xsd.schema.error_log:
                            self.add_finding(Error(error.line - 1, self, error.message))

            except ValueError:
                self.add_finding(
                    Error(
                        self.doc.sourceline - 1,
                        self,
                        f"Unsupported schema: "
                        f"{self.doc.nsmap.get(self.doc.prefix)}",
                    )
                )

        except etree.ParseError as pe:
            self.add_finding(Error(pe.position[0] - 1, self, str(pe)))
