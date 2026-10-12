from enum import nonmember

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, p, s


class SLMFileType(IntEnumProperties, p("label"), s("type")):
    _symmetric_builtins_ = [s("name", case_fold=True)]
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
