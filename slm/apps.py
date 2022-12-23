from django.apps import AppConfig
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver
from django.core.checks import Warning, register
from django.utils.translation import gettext as _


@register()
def check_permissions_setting(**kwargs):
    from django.conf import settings
    permissions = getattr(settings, 'SLM_PERMISSIONS', None)
    if permissions:
        try:
            from django.utils.module_loading import import_string
            import_string(permissions)
        except ImportError:
            return [
                Warning(
                    _(
                        f'Was unable to load SLM_PERMISSIONS callable: '
                        f'{permissions}'
                    ),
                    hint=_(
                        'Set SLM_PERMISSIONS to the import string for a '
                        'callable that returns a queryset of valid system'
                        'permissions.'
                    ),
                    id='slm.W001',
                )
            ]
    return []


class SLMConfig(AppConfig):
    name = 'slm'

    # space is used as a workaround to alphabetically push SLM to the
    # top of the admin
    verbose_name = " SLM"

    def ready(self):

        # don't remove these includes - they ensure signals are connected
        from slm import signals as slm_signals
        from slm.models import Site
        from slm.receivers import (
            event_emailers,  # register signal receivers that send emails
        )
        from slm.receivers import (
            event_loggers,  # register signal receivers that log events
        )
        from slm.receivers import cleanup, index

        @receiver(post_init, sender=Site)
        def site_init(sender, instance, **kwargs):
            # publishing may be tracked through a status update or if the
            # last_publish timestamp changes

            instance._slm_pre_status = instance.status
            instance._slm_last_publish = instance.last_publish
            if instance.pk is None:
                instance._slm_pre_status = None
                instance._slm_last_publish = None

        @receiver(post_save, sender=Site)
        def site_save(
            sender, instance, created, raw, using, update_fields, **kwargs
        ):
            if (
                hasattr(instance, '_slm_pre_status') and
                instance._slm_pre_status != instance.status
            ) or (
                hasattr(instance, '_slm_last_publish') and
                instance._slm_last_publish != instance.last_publish
            ):
                slm_signals.site_status_changed.send(
                    sender=self,
                    site=instance,
                    previous_status=instance._slm_pre_status,
                    new_status=instance.status
                )

