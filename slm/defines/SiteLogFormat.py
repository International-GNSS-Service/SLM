from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class SiteLogFormat(IntegerChoices, s('mimetype')):

    LEGACY     = 0, _('Legacy (ASCII)'), 'text/plain'
    GEODESY_ML = 1, _('GeodesyML'),      'application/xml'
    JSON =       2, _('JSON'),           'application/json'
