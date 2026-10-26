from typing import Annotated

from enum_properties import StrEnumProperties, Symmetric


class CoordinateMode(StrEnumProperties):
    label: Annotated[str, Symmetric(case_fold=True)]
    help: str

    # fmt: off
    INDEPENDENT = "I", "INDEPENDENT", "User specifies station coordinates in ECEF and LLH seperately."
    ECEF        = "E", "ECEF",        "User specifies station coordinates in ECEF, LLH coordinates are calculated by the system."
    LLH         = "L", "LLH",         "User specifies station coordinates in LLH, ECEF coordinates are calculated by the system."
    # fmt: on
