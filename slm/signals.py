"""
All SLM specific signals sent by the system are defined here. These signals
mostly include events relating to the site log edit/moderate/publish lifecycle.

All signals contain a request object that holds the request that initiated the
event. This object is provided mostly for logging purposes and is not
guaranteed to be non-null.
"""
from django import dispatch

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
site_proposed = dispatch.Signal()

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
site_published = dispatch.Signal()

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
section_edited = dispatch.Signal()

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
section_added = dispatch.Signal()

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
section_deleted = dispatch.Signal()

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
fields_flagged = dispatch.Signal()

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
flags_cleared = dispatch.Signal()

"""
Sent when a user uploads a site log.

:param sender: The sending object (unreliable).
:param site: The Site object. 
:param user: The user that uploaded the site log.
:param timestamp: The time the site log was uploaded.
:param request: The Django request object that contained the upload.
:param format: The site log upload format.
:param updated_sections: The list of section objects that were updated.
:param kwargs: Misc other key word arguments
"""
site_log_uploaded = dispatch.Signal()

"""
Sent when a user requests a site log be reviewed and published by moderators.

:param sender: The sending object (unreliable).
:param review_request: The review request object.
:param request: The Django request object that contained the request.
:param kwargs: Misc other key word arguments
"""
review_requested = dispatch.Signal()

"""
Sent when a moderator rejects edits requested for publish in a review request.

:param sender: The sending object (unreliable).
:param review_request: The review request object that was rejected.
:param request: The Django request object that contained the rejection.
:param rejecter: The user that rejected the changes.
:param kwargs: Misc other key word arguments
"""
changes_rejected = dispatch.Signal()

"""
Sent when an alert is issued.

:param sender: The sending object (unreliable).
:param alert: The alert object that was issued.
:param issuer: The issuing moderator.
:param kwargs: Misc other key word arguments
"""
alert_issued = dispatch.Signal()

"""
Sent when an alert is cleared.

:param sender: The sending object (unreliable).
:param alert: The alert object that was issued.
:param clearer: The clearing user.
:param kwargs: Misc other key word arguments
"""
alert_cleared = dispatch.Signal()
