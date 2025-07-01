from django.dispatch import receiver

from slm import signals as slm_signals
from slm.defines import SiteLogStatus


@receiver(slm_signals.site_status_changed)
def index_site(sender, site, previous_status, new_status, reverted=False, **kwargs):
    from slm.models import ArchiveIndex

    if site.last_publish and (
        previous_status in SiteLogStatus.active_states()
        and new_status not in SiteLogStatus.active_states()
    ):
        ArchiveIndex.objects.close_index(site)
    elif (
        site.last_publish
        and previous_status in SiteLogStatus.active_states()
        and previous_status is not SiteLogStatus.PUBLISHED
        and new_status is SiteLogStatus.PUBLISHED
        and not reverted
    ):
        # catch an edge case where a section publish triggers a whole log publish
        # these signals/edit state diagram needs to be cleaned up. this code is
        # too hard to follow.
        ArchiveIndex.objects.add_index(site)


@receiver(slm_signals.site_published)
def publish_site(sender, site, **kwargs):
    from slm.models import ArchiveIndex

    ArchiveIndex.objects.add_index(site)


# for image and file attachment changes we simply regenerate the GeodesyML file
# at the current index. This can lead to some GeodesyML files with different
# attachment lists but the same file name in circulation. An alternative
# approach would be to generate a new index for each attachment change but this
# would produce lots of identical legacy logs with different timestamps/names.
# The current approach is fine for now - the attachments are largely of
# ancillary benefit.
@receiver(slm_signals.site_file_published)
def log_file_published(sender, site, user, timestamp, request, upload, **kwargs):
    from slm.defines import SiteLogFormat
    from slm.models import ArchiveIndex

    ArchiveIndex.objects.regenerate(site, log_format=SiteLogFormat.GEODESY_ML)


@receiver(slm_signals.site_file_unpublished)
def log_file_unpublished(sender, site, user, timestamp, request, upload, **kwargs):
    from slm.defines import SiteLogFormat
    from slm.models import ArchiveIndex

    ArchiveIndex.objects.regenerate(site, log_format=SiteLogFormat.GEODESY_ML)


@receiver(slm_signals.site_file_deleted)
def log_file_deleted(sender, site, user, timestamp, request, upload, **kwargs):
    from slm.defines import SiteFileUploadStatus, SiteLogFormat, SLMFileType
    from slm.models import ArchiveIndex

    if upload.status is SiteFileUploadStatus.PUBLISHED and upload.file_type in [
        SLMFileType.SITE_IMAGE,
        SLMFileType.ATTACHMENT,
    ]:
        ArchiveIndex.objects.regenerate(site, log_format=SiteLogFormat.GEODESY_ML)
