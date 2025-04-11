from typing import Callable, Dict, List, Tuple, Union

from slm.defines import (
    GeodesyMLVersion,
)
from slm.parsing import (
    BaseBinder,
    Error,
    to_date,
    to_str,
)
from slm.parsing.xsd.parser import Parameter, Section, SiteLogParser


class SiteLogBinder(BaseBinder):
    """ """

    parsed: SiteLogParser

    TRANSLATION_TABLE: Dict[
        GeodesyMLVersion,
        Dict[
            Tuple[Tuple[Union[int, None]], str],
            List[Tuple[str, Union[Tuple[str, Callable], List[Tuple[str, Callable]]]]],
        ],
    ] = {
        GeodesyMLVersion.v0_4: {
            ((0,), "/geo:GeodesyML/geo:siteLog/geo:formInformation"): [
                ("geo:preparedBy", ("prepared_by", to_str)),
                ("geo:datePrepared", ("date_prepared", to_date)),
                ("geo:reportType", ("report_type", to_str)),
            ]
        }
    }

    TRANSLATION_TABLE[GeodesyMLVersion.v0_5] = {
        (
            (0,),
            "/geo:GeodesyML/geo:siteLog/geo:formInformation/geo:FormInformation",
        ): TRANSLATION_TABLE[GeodesyMLVersion.v0_4][
            ((0,), "/geo:GeodesyML/geo:siteLog/geo:formInformation")
        ],
    }

    def __init__(self, parsed: SiteLogParser):
        super().__init__(parsed)
        binding_map = self.TRANSLATION_TABLE.get(parsed.xsd, None)
        if binding_map is None:
            parsed.add_finding(
                Error(
                    parsed.doc.sourceline - 1,
                    parsed,
                    f"Unsupported schema for data binding: "
                    f"{parsed.doc.nsmap.get(parsed.doc.prefix)}",
                )
            )

        namespaces = {"geo": self.parsed.xsd.xmlns}
        for (index, path), bindings in binding_map.items():
            trees = self.parsed.doc.xpath(path, namespaces=namespaces)

            # if the last element in the index is None it means we expect to
            # to find more than one
            order = 0 if index[-1] is None else None
            if trees:
                for tree in trees:
                    section = parsed.add_section(
                        Section(
                            tree,
                            self.parsed,
                            *([*index, order] if order is not None else index),
                        )
                    )
                    for path, binding in bindings:
                        elements = tree.xpath(path, namespaces=namespaces)
                        if elements:
                            parameter = section.add_parameter(
                                Parameter(elements, parsed, section)
                            )
                            for param, bind in (
                                [binding] if isinstance(binding, tuple) else binding
                            ):
                                parameter.bind(param, bind(parameter.value))

                    if order is not None:
                        order += 1
