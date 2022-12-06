from django_enum import IntegerChoices
from enum_properties import s, p
from django.utils.translation import gettext as _


class SiteLogStatus(IntegerChoices, p('help')):

    _symmetric_builtins_ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    DORMANT = (
        0,
        _('Dormant'),
        _('Site is inactive and updates to the log are no longer published.')
    )

    PENDING = (
        1,
        _('Pending'),
        _(
            'Site is pending approval, updates will not be published until '
            'the site is activated.'
        )
    )

    UPDATED = (
        2,
        _('Updated'),
        _('Site log or section has unpublished updates.')
    )

    PUBLISHED = (
        3,
        _('Published'),
        _('Site log or section is published with no unpublished changes.')
    )

    EMPTY = (
        4,
        _('Empty'),
        _('Site log or section is empty.')
    )

    @property
    def css(self):
        return f'slm-status-{self.label.lower()}'
    
    @property
    def color(self):
        from django.conf import settings
        return getattr(settings, 'SLM_STATUS_COLORS', {}).get(self, None)

    def merge(self, sibling):
        """
        Returns the correct status value to use when sibling status values are
        being combined into one parent status value.
        """
        if sibling is not None and sibling.value < self.value:
            return sibling
        return self

    def set(self, child):
        """
        Returns the correct status value to use when this status is being set
        to the aggregate status of its children.
        """
        if self in {
            SiteLogStatus.PUBLISHED,
            SiteLogStatus.UPDATED,
            SiteLogStatus.EMPTY
        }:
            return child
        return self.merge(child)

    def __str__(self):
        return self.label
