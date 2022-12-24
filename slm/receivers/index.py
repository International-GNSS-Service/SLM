from django.dispatch import receiver
from slm import signals as slm_signals
from slm.defines import SiteLogStatus


@receiver(slm_signals.site_status_changed)
def index_site(sender, site, previous_status, new_status, **kwargs):
    from slm.models import SiteIndex
    active_states = {
        SiteLogStatus.IN_REVIEW,
        SiteLogStatus.UPDATED,
        SiteLogStatus.PUBLISHED
    }

    if new_status == SiteLogStatus.PUBLISHED:
        SiteIndex.objects.add_index(site)
    elif site.last_publish and (
        previous_status in active_states and
        new_status not in active_states
    ):
        SiteIndex.objects.close_index(site)
