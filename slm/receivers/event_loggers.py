from django.dispatch import receiver
from slm import signals as slm_signals
from ipware import get_client_ip
import logging


logger = logging.getLogger(__name__)


@receiver(slm_signals.site_published)
def log_publish(sender, site, user, timestamp, request, section, **kwargs):
    from slm.models import LogEntry
    from slm.defines import LogEntryType

    LogEntry.objects.create(
        type=LogEntryType.PUBLISH,
        user=user,
        site=site,
        site_log_object=section,
        epoch=timestamp,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.site_proposed)
def log_propose(sender, site, user, timestamp, request, agencies, **kwargs):
    from slm.models import LogEntry
    from slm.defines import LogEntryType

    LogEntry.objects.create(
        type=LogEntryType.NEW_SITE,
        user=user,
        site=site,
        site_log_object=site,
        epoch=timestamp,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.section_edited)
def log_edit(
        sender,
        site,
        user,
        timestamp,
        request,
        section,
        fields,
        **kwargs
):
    from slm.models import LogEntry
    from slm.defines import LogEntryType

    LogEntry.objects.create(
        type=LogEntryType.UPDATE,
        user=user,
        site=site,
        site_log_object=section,
        epoch=timestamp,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.section_added)
def log_add(sender, site, user, timestamp, request, section, **kwargs):
    from slm.models import LogEntry
    from slm.defines import LogEntryType

    LogEntry.objects.create(
        type=LogEntryType.ADD,
        user=user,
        site=site,
        site_log_object=section,
        epoch=timestamp,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.section_deleted)
def log_delete(sender, site, user, timestamp, request, section, **kwargs):
    from slm.models import LogEntry
    from slm.defines import LogEntryType

    LogEntry.objects.create(
        type=LogEntryType.DELETE,
        user=user,
        site=site,
        site_log_object=section,
        epoch=timestamp,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.site_file_uploaded)
def log_file_upload(sender, site, user, timestamp, request, upload, **kwargs):
    from slm.models import LogEntry
    from slm.defines import LogEntryType

    LogEntry.objects.create(
        type=(
            LogEntryType.LOG_UPLOAD if upload.file_type.SITE_LOG
            else LogEntryType.FILE_UPLOAD
        ),
        user=user,
        site=site,
        epoch=timestamp,
        ip=get_client_ip(request)[0] if request else None
    )

