from django_enum import TextChoices
from enum_properties import s


class FractureSpacing(TextChoices):
    _symmetric_builtins_ = [s("name", case_fold=True), s("label", case_fold=True)]

    # fmt: off
    ZERO                          =   "0", "0 cm"
    LESS_THAN_10_CM               =   "1", "1-10 cm"
    MORE_THAN_11_LESS_THAN_50_CM  =  "11", "11-50 cm"
    MORE_THAN_51_LESS_THAN_200_CM =  "51", "51-200 cm"
    OVER_200_CM                   = "200", "over 200 cm"
    # fmt: on

    def __str__(self):
        return str(self.label)
