from django.dispatch import receiver
from slm import signals as slm_signals
from slm.defines import SiteLogStatus


@receiver(slm_signals.site_status_changed)
def index_site(sender, site, previous_status, new_status, **kwargs):
    from slm.models import ArchiveIndex
    if site.last_publish and (
        previous_status in SiteLogStatus.active_states() and
        new_status not in SiteLogStatus.active_states()
    ):
        ArchiveIndex.objects.close_index(site)


@receiver(slm_signals.site_published)
def publish_site(sender, site, **kwargs):
    from slm.models import ArchiveIndex
    ArchiveIndex.objects.add_index(site)
