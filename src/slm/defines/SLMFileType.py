from enum import nonmember
from typing import Annotated

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, Symmetric


class SLMFileType(IntEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: str
    type: Annotated[str, Symmetric()]

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    SITE_LOG   = 1, _("Site Log"),   "log"
    SITE_IMAGE = 2, _("Site Image"), "image"
    ATTACHMENT = 3, _("Attachment"), "attachment"
    # fmt: on

    @staticmethod
    def icon(mimetype):
        return f"bi bi-filetype-{mimetype.split('/')[-1]}"

    def __str__(self):
        return str(self.label)
