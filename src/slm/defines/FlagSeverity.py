from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s


class FlagSeverity(IntegerChoices):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    BLOCK_SAVE    = 1, _("Block Save")
    BLOCK_PUBLISH = 2, _("Block Publish")
    NOTIFY        = 3, _("Notify")
    # fmt: on

    def __str__(self):
        return str(self.label)
