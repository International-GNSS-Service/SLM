from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s


class SLMFileType(IntegerChoices, s("type")):
    _symmetric_builtins_ = [s("name", case_fold=True)]

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
