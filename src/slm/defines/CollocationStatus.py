from django_enum import TextChoices
from enum_properties import s


class CollocationStatus(TextChoices):
    _symmetric_builtins_ = [s("name", case_fold=True), s("label", case_fold=True)]

    # fmt: off
    PERMANENT = "P", "PERMANENT"
    HOURLY    = "M", "MOBILE"
    # fmt: on

    def __str__(self):
        return str(self.label)
