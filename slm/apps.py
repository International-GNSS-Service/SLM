from django.apps import AppConfig


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
            site_record,
            cleanup
        )
