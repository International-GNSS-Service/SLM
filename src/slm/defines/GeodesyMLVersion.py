from pathlib import Path

from django.utils.functional import cached_property
from django_enum import IntegerChoices
from enum_properties import s


class GeodesyMLVersion(IntegerChoices, s("version"), s("xmlns", case_fold=True)):
    _symmetric_builtins_ = [s("name", case_fold=True), s("label", case_fold=True)]

    # fmt: off
    # name  value     label      version              xmlns
    v0_4 = 1, "GeodesyML/0.4", 0.4, "urn:xml-gov-au:icsm:egeodesy:0.4"
    v0_5 = 2, "GeodesyML/0.5", 0.5, "urn:xml-gov-au:icsm:egeodesy:0.5"
    # fmt: on

    def __str__(self):
        return self.label

    @classmethod
    def latest(cls):
        return [ver for ver in cls][-1]

    @cached_property
    def schema(self):
        from lxml.etree import XMLParser, XMLSchema, parse

        from slm.parsing import xsd
        from slm.parsing.xsd.resolver import CachedResolver

        parser = XMLParser()
        parser.resolvers.add(CachedResolver())
        # todo - do this with importlib.resources ?
        return XMLSchema(
            etree=parse(
                str(
                    Path(xsd.__path__[0])
                    / "geodesyml"
                    / str(self.version)
                    / "geodesyML.xsd"
                ),
                parser,
            )
        )

    @cached_property
    def template(self):
        from django.template.loader import get_template

        return get_template(f"slm/sitelog/xsd/geodesyml_{self.version}.xml")
