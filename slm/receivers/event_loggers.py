import logging
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from ipware import get_client_ip
from slm import signals as slm_signals
from django.utils.timezone import now


logger = logging.getLogger(__name__)


@receiver(slm_signals.site_published)
def log_publish(sender, site, user, timestamp, request, section, **kwargs):
    from slm.defines import LogEntryType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=LogEntryType.PUBLISH,
        user=user,
        site=site,
        section=(
            ContentType.objects.get_for_model(section) if section else None
        ),
        subsection=getattr(section, 'subsection', None),
        timestamp=timestamp or now(),
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.site_proposed)
def log_propose(sender, site, user, timestamp, request, agencies, **kwargs):
    from slm.defines import LogEntryType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=LogEntryType.SITE_PROPOSED,
        user=user,
        site=site,
        timestamp=timestamp or now(),
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
    from slm.defines import LogEntryType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=LogEntryType.UPDATE,
        user=user,
        site=site,
        section=(
            ContentType.objects.get_for_model(section) if section else None
        ),
        subsection=getattr(section, 'subsection', None),
        timestamp=timestamp or now(),
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.section_added)
def log_add(sender, site, user, timestamp, request, section, **kwargs):
    from slm.defines import LogEntryType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=LogEntryType.ADD,
        user=user,
        site=site,
        section=(
            ContentType.objects.get_for_model(section) if section else None
        ),
        subsection=getattr(section, 'subsection', None),
        timestamp=timestamp or now(),
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.section_deleted)
def log_delete(sender, site, user, timestamp, request, section, **kwargs):
    from slm.defines import LogEntryType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=LogEntryType.DELETE,
        user=user,
        site=site,
        section=(
            ContentType.objects.get_for_model(section) if section else None
        ),
        subsection=getattr(section, 'subsection', None),
        timestamp=timestamp or now(),
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.site_file_uploaded)
def log_file_upload(sender, site, user, timestamp, request, upload, **kwargs):
    from slm.defines import LogEntryType, SLMFileType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=({
          SLMFileType.SITE_IMAGE: LogEntryType.IMAGE_UPLOAD,
          SLMFileType.SITE_LOG: LogEntryType.LOG_UPLOAD,
          SLMFileType.ATTACHMENT: LogEntryType.ATTACHMENT_UPLOAD
        }.get(upload.file_type, LogEntryType.LOG_UPLOAD)),
        user=user,
        site=site,
        timestamp=timestamp or now(),
        file=upload,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.site_file_published)
def log_file_published(
    sender, site, user, timestamp, request, upload, **kwargs
):
    from slm.defines import LogEntryType, SLMFileType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=(
            LogEntryType.IMAGE_PUBLISH
            if upload.file_type == SLMFileType.SITE_IMAGE
            else LogEntryType.ATTACHMENT_PUBLISH
        ),
        user=user,
        site=site,
        timestamp=timestamp or now(),
        file=upload,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.site_file_unpublished)
def log_file_unpublished(
    sender, site, user, timestamp, request, upload, **kwargs
):
    from slm.defines import LogEntryType, SLMFileType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=(
            LogEntryType.IMAGE_UNPUBLISH
            if upload.file_type == SLMFileType.SITE_IMAGE
            else LogEntryType.ATTACHMENT_UNPUBLISH
        ),
        user=user,
        site=site,
        timestamp=timestamp or now(),
        file=upload,
        ip=get_client_ip(request)[0] if request else None
    )


@receiver(slm_signals.site_file_deleted)
def log_file_deleted(sender, site, user, timestamp, request, upload, **kwargs):
    from slm.defines import LogEntryType, SLMFileType
    from slm.models import LogEntry

    LogEntry.objects.create(
        type=(
            LogEntryType.IMAGE_DELETE
            if upload.file_type == SLMFileType.SITE_IMAGE
            else LogEntryType.ATTACHMENT_DELETE
        ),
        user=user,
        site=site,
        timestamp=timestamp or now(),
        file=None,
        ip=get_client_ip(request)[0] if request else None
    )
