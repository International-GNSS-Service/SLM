from django.apps import AppConfig
from django.dispatch import receiver
from django.db.models.signals import post_init, post_save


class SLMConfig(AppConfig):
    name = 'slm'

    # space is used as a workaround to alphabetically push SLM to the
    # top of the admin
    verbose_name = " SLM"

    def ready(self):

        # don't remove these includes - they ensure signals are connected
        from slm import signals as slm_signals
        from slm.receivers import (
            event_emailers,  # register signal receivers that send emails
            event_loggers,  # register signal receivers that log events
            index,
            cleanup
        )
        from slm.models import Site

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

        from django.conf import settings
        import os
        import stat
        for path in [settings.MEDIA_ROOT, settings.SITE_DIR / 'media']:

            for root, dirs, files in os.walk(path):
                for filename in files:
                    try:
                        os.chmod(os.path.join(root, filename), stat.S_IRWXG)
                    except OSError:
                        pass
                for dirname in dirs:
                    try:
                        os.chmod(os.path.join(root, dirname), stat.S_IRWXG)
                    except OSError:
                        pass

