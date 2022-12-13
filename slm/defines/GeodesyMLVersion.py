from django_enum import IntegerChoices
from enum_properties import s
from pathlib import Path
from django.utils.functional import cached_property


class GeodesyMLVersion(
    IntegerChoices,
    s('version'),
    s('xmlns', case_fold=True)
):
    _symmetric_builtins_ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    # name  value     label      version              xmlns
    v0_4   = 0,  'GeodesyML/0.4',  0.4,  'urn:xml-gov-au:icsm:egeodesy:0.4'
    v0_5   = 1,  'GeodesyML/0.5',  0.5,  'urn:xml-gov-au:icsm:egeodesy:0.5'

    def __str__(self):
        return self.label

    @classmethod
    def latest(cls):
        return [ver for ver in cls][-1]

    @cached_property
    def schema(self):
        from lxml.etree import XMLSchema
        from slm import xsd
        # todo - do this with importlib.resources ?
        return XMLSchema(
            file=str(
                Path(xsd.__path__[0]) / 'geodesyml' / str(self.version)
                / 'geodesyML.xsd'
            )
        )
