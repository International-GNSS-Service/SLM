from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import p, s


class SiteLogFormat(
    IntegerChoices,
    s("mimetype", case_fold=True),
    p("icon"),
    s("ext", case_fold=True),
    s("alts", case_fold=True),
    s("alt_exts", case_fold=True),
):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    # name       value     label             mimetype             icon                ext             alts                  alt_exts
    LEGACY      = 1, _("Legacy (ASCII)"), "text/plain",       "bi bi-file-text",     "log",  ["text", "txt", "legacy"], ["txt", "sitelog"]
    GEODESY_ML  = 2, _("GeodesyML"),      "application/xml",  "bi bi-filetype-xml",  "xml",  ["xml"],                   ["gml"]
    JSON        = 3, _("JSON"),           "application/json", "bi bi-filetype-json", "json", ["json", "js"],            ["js"]
    ASCII_9CHAR = 4, _("ASCII (9-Char)"), "text/plain",       "bi bi-file-text",     "log",  ["text", "txt", "9char"],  ["txt", "sitelog"]
    # fmt: on

    def __str__(self):
        return str(self.label)
