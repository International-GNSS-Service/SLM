from django_enum import IntegerChoices
from enum_properties import s, p
from django.utils.translation import gettext as _


class SiteLogFormat(IntegerChoices, s('mimetype'), p('icon'), s('ext')):

    LEGACY     = 0, _('Legacy (ASCII)'), 'text/plain'      , 'bi bi-file-text', 'log'
    GEODESY_ML = 1, _('GeodesyML'),      'application/xml',  'bi bi-filetype-xml', 'xml'
    JSON =       2, _('JSON'),           'application/json', 'bi bi-filetype-json', 'json'

    def __str__(self):
        return self.label
