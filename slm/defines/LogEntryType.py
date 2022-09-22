from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class LogEntryType(IntegerChoices):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    NEW_SITE = 1, _('New Site')
    ADD      = 2, _('Add')
    UPDATE   = 3, _('Update')
    DELETE   = 4, _('Delete')
    PUBLISH  = 5, _('Publish')
