from django_enum import IntegerChoices
from django.utils.translation import gettext as _


class SLMFileType(IntegerChoices):

    SITE_LOG    = 0, _('Site Log')
    SITE_IMAGE = 1, _('Site Image')
    ATTACHMENT = 2, _('Attachment')

    @staticmethod
    def icon(mimetype):
        return f'bi bi-filetype-{mimetype.split("/")[-1]}'

    def __str__(self):
        return self.label
