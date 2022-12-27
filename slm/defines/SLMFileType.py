from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s


class SLMFileType(IntegerChoices, s('type')):

    _symmetric_builtins_ = [s('name', case_fold=True)]

    SITE_LOG   = 0, _('Site Log'),   'log'
    SITE_IMAGE = 1, _('Site Image'), 'image'
    ATTACHMENT = 2, _('Attachment'), 'attachment'

    @staticmethod
    def icon(mimetype):
        return f'bi bi-filetype-{mimetype.split("/")[-1]}'

    def __str__(self):
        return str(self.label)
