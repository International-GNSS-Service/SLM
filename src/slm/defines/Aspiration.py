from django_enum import TextChoices
from enum_properties import s


class Aspiration(TextChoices):
    _symmetric_builtins_ = [s("name", case_fold=True), s("label", case_fold=True)]

    UNASPIRATED = "U", "UNASPIRATED"
    NATURAL = "N", "NATURAL"
    FAN = "F", "FAN"

    def __str__(self):
        return str(self.label)
