"""
All SLM specific :doc:`django:topics/signals` sent by the system are defined here.
These signals mostly include events relating to the site log edit/moderate/publish life
cycle.

All signals contain a request object that holds the request that initiated the
event. This object is provided mostly for logging purposes and is not
guaranteed to be non-null.
"""

import sys

from django.dispatch import Signal
from django.utils.module_loading import import_string

site_proposed = Signal()
"""
Signal sent when a new site is proposed.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that proposed the new site.
:param timestamp: The time the request was received
:param request: The Django request object that initiated the proposal.
:param agencies: The Agencies identified by the requester as the 
    responsible agencies.
:param kwargs: Misc other key word arguments
"""


site_published = Signal()
"""
Sent when a site log is published, or when a section of a site log is
published.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that published the site log.
:param timestamp: The time the site log was published.
:param request: The Django request object that initiated the publish.
:param section: None if the entire site log was published, if an individual
    section was published this will be the Section object instance.
:param kwargs: Misc other key word arguments
"""


site_status_changed = Signal()
"""
Sent when a site log's status changes. Its possible that both the previous and
new status states are Published. If this happens a site log was edited and
published simultaneously. The published timestamp will have increased.

:param sender: The sending object (unreliable).
:param site: The Site object.
:param previous_status: The previous status
:param new_status: The new status
:param reverted: If true this status change was the result of a reversion
:param kwargs: Misc other key word arguments
"""


section_edited = Signal()
"""
Sent when a site log section is edited.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that edited the site log section.
:param timestamp: The time the site log section was edited.
:param request: The Django request object that contained the edit.
:param section: The section object that was edited.
:param fields: The list of edited fields
:param kwargs: Misc other key word arguments
"""


section_added = Signal()
"""
Sent when a site log section is added.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that added the site log section.
:param timestamp: The time the site log section was added.
:param request: The Django request object that contained the add.
:param section: The section object that was added.
:param kwargs: Misc other key word arguments
"""


section_deleted = Signal()
"""
Sent when a site log section is deleted.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that deleted the site log section.
:param timestamp: The time the site log section was deleted.
:param request: The Django request object that contained the delete.
:param section: The section object that was deleted.
:param kwargs: Misc other key word arguments
"""


fields_flagged = Signal()
"""
Sent when a site log section has fields flagged.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that added the flags or performed the action that caused
 the flags to be added.
:param timestamp: The time the site log section was flagged.
:param request: The Django request object that added or triggered the flags.
:param section: The section object concerned.
:param fields: The list of fields that were flagged.
:param kwargs: Misc other key word arguments
"""


flags_cleared = Signal()
"""
Sent when a site log section has fields flagged.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that removed the flags or performed the action that
    caused the flags to be removed.
:param timestamp: The time the site log section was flagged.
:param request: The Django request object that removed or triggered the flags
    to be cleared.
:param section: The section object concerned.
:param fields: The list of fields that were cleared of flags.
:param clear: True if the section has no remaining flags - false otherwise.
:param kwargs: Misc other key word arguments
"""


site_file_uploaded = Signal()
"""
Sent when a user uploads a site log.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that uploaded the site log.
:param timestamp: The time the site log was uploaded.
:param request: The Django request object that contained the upload.
:param upload: The uploaded file (SiteFileUpload).
:param kwargs: Misc other key word arguments
"""


site_file_published = Signal()
"""
Sent when a moderator publishes a site file upload - could be an attachment or
an image.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that published the file.
:param timestamp: The time the file was published.
:param request: The Django request object that contained the upload.
:param upload: The uploaded file (SiteFileUpload).
:param kwargs: Misc other key word arguments
"""


site_file_unpublished = Signal()
"""
Sent when a moderator retracts a site file upload - could be an attachment
or an image.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that unpublished the file.
:param timestamp: The time the file was unpublished.
:param request: The Django request object that contained the upload.
:param upload: The uploaded file (SiteFileUpload).
:param kwargs: Misc other key word arguments
"""


site_file_deleted = Signal()
"""
Sent when a user deletes a site file upload through the API. The file must be
a type other than a site log - could be an attachment or an image.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that deleted the file.
:param timestamp: The time the file was deleted.
:param request: The Django request object that contained the upload.
:param upload: The uploaded file (SiteFileUpload).
:param kwargs: Misc other key word arguments
"""


review_requested = Signal()
"""
Sent when a user requests a site log be reviewed and published by moderators.

:param sender: The sending object (unreliable).
:param site: The site the reviews were requested for.
:param detail: The user given reasons for requesting the update (if any).
:param request: The Django request object that contained the request.
:param kwargs: Misc other key word arguments
"""

updates_rejected = Signal()
"""
Sent when a moderator rejects edits requested for publish in a review request.

:param sender: The sending object (unreliable).
:param site: The site the updates were rejected for.
:param detail: The user given reasons for rejecting the update (if any).
:param request: The Django request object that contained the rejection.
:param kwargs: Misc other key word arguments
"""


alert_issued = Signal()
"""
Sent when an alert is issued.

:param sender: The sending object (unreliable).
:param alert: The alert object that was issued.
:param kwargs: Misc other key word arguments
"""


alert_cleared = Signal()
"""
Sent when an alert is cleared.

:param sender: The sending object (unreliable).
:param alert: The alert object that was issued.
:param kwargs: Misc other key word arguments
"""

_signal_names_ = {
    value: f"slm.signals.{key}"
    for key, value in sys._getframe().f_globals.items()
    if isinstance(value, Signal)
}


def signal_name(signal):
    """
    Given a signal object - try to determine its name (import path). This is
    not easy and prone to failure so don't use it for anything critical.
    """
    if not isinstance(signal, Signal):
        return signal
    name = _signal_names_.get(signal, None)
    if name:
        return name
    return {
        value: f"{signal.__module__}.{key}"
        for key, value in vars(import_string(signal.__module__)).items()
        if isinstance(value, Signal)
    }.get(signal, str(signal))
