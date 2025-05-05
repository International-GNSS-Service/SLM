from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import p, s

from slm.defines import SLMFileType


class SiteFileUploadStatus(IntegerChoices, p("help")):
    """
    Depending on file type different uploads will have different relevant
    status tuples.
    """

    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    UNPUBLISHED = 1, _("Unpublished File"),  _("The file is pending moderation before it will be made public.")
    PUBLISHED   = 2, _("Published File"),    _("The file is published and is publicly available as an attachment to the site.")
    INVALID     = 3, _("Invalid Site Log"),  _("The file did not pass validation.")
    WARNINGS    = 4, _("Warnings Site Log"), _("The file is valid but has some warnings.")
    VALID       = 5, _("Valid Site Log"),    _("The file is valid.")
    # fmt: on

    @classmethod
    def status_by_filetype(cls, filetype):
        if filetype == SLMFileType.SITE_LOG:
            return [cls.INVALID, cls.WARNINGS, cls.VALID]
        elif filetype == SLMFileType.SITE_IMAGE:
            return [cls.PUBLISHED, cls.UNPUBLISHED]
        else:
            return [en for en in cls]

    @property
    def css(self):
        return f"slm-upload-{self.label.lower()}"

    @property
    def color(self):
        from django.conf import settings

        return getattr(settings, "SLM_FILE_COLORS", {}).get(self, None)

    def __str__(self):
        return str(self.label)
