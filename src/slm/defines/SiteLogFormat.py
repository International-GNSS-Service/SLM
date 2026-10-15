from enum import nonmember
from typing import Annotated

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, Symmetric


class SiteLogFormat(IntEnumProperties):
    name: Annotated[str, Symmetric(case_fold=True)]
    label: str
    mimetype: Annotated[str, Symmetric(case_fold=True)]
    icon: str
    ext: Annotated[str, Symmetric(case_fold=True)]
    alts: Annotated[list[str], Symmetric(case_fold=True)]
    supersedes: list[int]

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    # name       value     label             mimetype             icon                ext                   alts                     supersedes
    LEGACY      = 1, _("Legacy (ASCII)"), "text/plain",       "bi bi-file-text",     "log",  ["text", "txt", "legacy", "sitelog"], []
    GEODESY_ML  = 2, _("GeodesyML"),      "application/xml",  "bi bi-filetype-xml",  "xml",  ["xml", "gml"],                       []
    JSON        = 3, _("JSON"),           "application/json", "bi bi-filetype-json", "json", ["json", "js"],                       []
    ASCII_9CHAR = 4, _("ASCII (9-Char)"), "text/plain",       "bi bi-file-text",     "log",  ["text", "txt", "9char", "sitelog"],  [1]  # supersedes LEGACY
    # fmt: on

    def __str__(self):
        return str(self.label)

    @property
    def suffix(self):
        """
        Fetch the configured suffix for this file type.
        """
        from django.conf import settings

        return getattr(
            settings,
            "SLM_FORMAT_EXTENSIONS",
            {fmt: fmt.ext for fmt in SiteLogFormat},
        )[self]
