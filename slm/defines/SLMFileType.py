from django_enum import IntegerChoices
from django.utils.translation import gettext as _


class SLMFileType(IntegerChoices):

    SITE_LOG    = 0, _('Site Log')
    SITE_IMAGE = 1, _('Site Image')
    UNKNOWN = 2, _('Unknown')
