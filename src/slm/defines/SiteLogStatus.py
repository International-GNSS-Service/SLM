from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import p, s


class SiteLogStatus(IntegerChoices, p("help")):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    FORMER    = 1, _("Former"),    _("Site is no longer maintained and logs are not published.")
    PROPOSED  = 2, _("Proposed"),  _("This is a new Site that has never been published.")
    UPDATED   = 3, _("Updated"),   _("Site log or section has unpublished updates.")
    PUBLISHED = 4, _("Published"), _("Site log or section is published with no unpublished changes.")
    EMPTY     = 5, _("Empty"),     _("Site log section is empty or deleted.")
    SUSPENDED = 6, _("Suspended"), _("Site has been temporarily suspended and does not appear in public data.")
    # fmt: on

    @property
    def css(self):
        return f"slm-status-{self.label.lower().replace(' ', '-')}"

    @property
    def color(self):
        from django.conf import settings

        return getattr(settings, "SLM_STATUS_COLORS", {}).get(self, None)

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
            SiteLogStatus.EMPTY,
        }:
            return child
        return self.merge(child)

    @classmethod
    def unpublished_states(cls):
        return {cls.UPDATED, cls.PROPOSED}

    @classmethod
    def active_states(cls):
        return {cls.UPDATED, cls.PUBLISHED}

    def __str__(self):
        return str(self.label)
