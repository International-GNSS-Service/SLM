from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import s


class LogEntryType(IntegerChoices):

    _symmetric_builtins_ = [s('name', case_fold=True)]

    SITE_PROPOSED     = 1, _('Site Proposed')
    ADD               = 2, _('Add')
    UPDATE            = 3, _('Update')
    DELETE            = 4, _('Delete')
    PUBLISH           = 5, _('Publish')
    LOG_UPLOAD        = 6, _('Log Upload')
    IMAGE_UPLOAD      = 7, _('Image Upload')
    ATTACHMENT_UPLOAD = 8, _('Attachment Upload')

    @property
    def css(self):
        return f'slm-log-' \
               f'{self.label.lower().replace("_", "-").replace(" ", "-")}'

    def __str__(self):
        return str(self.label)
