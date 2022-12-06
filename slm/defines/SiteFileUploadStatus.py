from django_enum import IntegerChoices
from enum_properties import s, p
from django.utils.translation import gettext as _
from slm.defines import SLMFileType


class SiteFileUploadStatus(IntegerChoices, p('help')):
    """
    Depending on file type different uploads will have different relevant
    status tuples.
    """

    _symmetric_builtins_ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    UNPUBLISHED = (
        0,
        _('Unpublished'),
        _('The file is pending moderation before it will be made public.')
    )

    PUBLISHED = (
        1,
        _('Published'),
        _(
            'The file is published and is publicly available as an attachment '
            'to the site.'
        )
    )

    INVALID = (
        2,
        _('Invalid'),
        _('The file did not pass validation.')
    )

    WARNINGS = (
        3,
        _('Warnings'),
        _('The file is valid but has some warnings.')
    )

    VALID = (
        4,
        _('Valid'),
        _('The file is valid.')
    )

    @classmethod
    def status_by_filetype(cls, filetype):
        if filetype == SLMFileType.SITE_LOG:
            return [cls.INVALID, cls.WARNINGS, cls.VALID]
        elif filetype == SLMFileType.SITE_IMAGE:
            return [cls.PUBLISHED, cls.UNPUBLISHED]
        else:
            return [en for en in cls]

    @property
    def css(self):
        return f'slm-upload-{self.label.lower()}'

    @property
    def color(self):
        from django.conf import settings
        return getattr(settings, 'SLM_FILE_COLORS', {}).get(self, None)

    def __str__(self):
        return self.label
