from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import p, s


class SiteLogFormat(IntegerChoices, s('mimetype'), p('icon'), s('ext')):

    _symmetric_builtins_ = [s('name', case_fold=True)]

    LEGACY     = 1, _('Legacy (ASCII)'), 'text/plain',       'bi bi-file-text',     'log'
    GEODESY_ML = 2, _('GeodesyML'),      'application/xml',  'bi bi-filetype-xml',  'xml'
    JSON =       3, _('JSON'),           'application/json', 'bi bi-filetype-json', 'json'

    def __str__(self):
        return str(self.label)
