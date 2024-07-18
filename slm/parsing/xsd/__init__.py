import sys
import typing as t

from lxml.etree import XMLSchema

from slm.defines import GeodesyMLVersion
from slm.parsing.xsd.binding import SiteLogBinder
from slm.parsing.xsd.parser import SiteLogParser

__all__ = [SiteLogBinder, SiteLogParser]


def load_schemas(
    xsd_versions: t.List[GeodesyMLVersion] = list(GeodesyMLVersion),
) -> t.List[XMLSchema]:
    if sys.stdout.isatty():
        from tqdm import tqdm

        schemas = []
        with tqdm(
            total=len(xsd_versions),
            desc="Loading",
            unit="schema",
            postfix={"xsd": None},
            disable=not sys.stdout.isatty(),
        ) as p_bar:
            for geo_version in xsd_versions:
                p_bar.set_postfix({"xsd": str(geo_version)})
                getattr(geo_version, "schema")
                schemas.append(geo_version.schema)
                p_bar.update(n=1)
        return schemas
    else:
        return [gml.schema for gml in xsd_versions]
