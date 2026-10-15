from enum import nonmember
from typing import Annotated

from enum_properties import StrEnumProperties, Symmetric


class FractureSpacing(StrEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: Annotated[str, Symmetric(case_fold=True)]

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    ZERO                          =   "0", "0 cm"
    LESS_THAN_10_CM               =   "1", "1-10 cm"
    MORE_THAN_11_LESS_THAN_50_CM  =  "11", "11-50 cm"
    MORE_THAN_51_LESS_THAN_200_CM =  "51", "51-200 cm"
    OVER_200_CM                   = "200", "over 200 cm"
    # fmt: on

    def __str__(self):
        return str(self.label)
