from django_enum import TextChoices
from enum_properties import s


class CollocationStatus(TextChoices):
    _symmetric_builtins_ = [s("name", case_fold=True), s("label", case_fold=True)]

    PERMANENT = "P", "PERMANENT"
    HOURLY = "M", "MOBILE"

    def __str__(self):
        return str(self.label)
