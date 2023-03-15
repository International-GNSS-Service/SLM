from django.dispatch import receiver
from slm import signals as slm_signals
from slm.defines import SiteLogStatus


@receiver(slm_signals.site_status_changed)
def index_site(sender, site, previous_status, new_status, **kwargs):
    from slm.models import ArchiveIndex
    if new_status == SiteLogStatus.PUBLISHED:
        ArchiveIndex.objects.add_index(site)
    elif site.last_publish and (
        previous_status in SiteLogStatus.active_states() and
        new_status not in SiteLogStatus.active_states()
    ):
        ArchiveIndex.objects.close_index(site)
