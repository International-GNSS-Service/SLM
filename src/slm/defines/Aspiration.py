from enum import nonmember

from enum_properties import StrEnumProperties, s


class Aspiration(StrEnumProperties, s("label", case_fold=True)):
    _symmetric_builtins_ = [s("name", case_fold=True)]
    do_not_call_in_templates = nonmember(True)

    # fmt: off
    UNASPIRATED = "U", "UNASPIRATED"
    NATURAL     = "N", "NATURAL"
    FAN         = "F", "FAN"
    # fmt: on

    def __str__(self):
        return str(self.label)
