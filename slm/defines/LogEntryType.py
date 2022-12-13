from django.utils.translation import gettext as _
from django_enum import IntegerChoices
from enum_properties import s


class LogEntryType(IntegerChoices):

    _symmetric_builtins_ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    NEW_SITE    = 1, _('New Site')
    ADD         = 2, _('Add')
    UPDATE      = 3, _('Update')
    DELETE      = 4, _('Delete')
    PUBLISH     = 5, _('Publish')
    LOG_UPLOAD  = 6, _('Log Upload')
    FILE_UPLOAD = 7, _('File Upload')

    @property
    def css(self):
        return f'slm-log-' \
               f'{self.label.lower().replace("_", "-").replace(" ", "-")}'

    def __str__(self):
        return self.label
