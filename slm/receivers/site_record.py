from django.dispatch import receiver
from slm import signals as slm_signals


@receiver(slm_signals.site_published)
def record_publish(sender, site, user, timestamp, request, section, **kwargs):
    pass


@receiver(slm_signals.site_proposed)
def record_propose(sender, site, user, timestamp, request, agencies, **kwargs):
    pass


@receiver(slm_signals.section_edited)
def record_edit(sender, site, user, timestamp, request, section, **kwargs):
    pass


@receiver(slm_signals.section_deleted)
def record_add(sender, site, user, timestamp, request, section, **kwargs):
    pass


@receiver(slm_signals.section_deleted)
def record_delete(sender, site, user, timestamp, request, section, **kwargs):
    pass
