import logging
from functools import partial

from django.apps import apps
from django.conf import settings
from django.dispatch import Signal, receiver
from django.utils.module_loading import import_string

from slm import signals as slm_signals
from slm.models import Site

logger = logging.getLogger(f"{__name__}")

# signal receivers are stored as weak references, so we need to make sure
# they don't get garbage collected
receivers = []


def issue_alert(alert_class, **kwargs):
    alert = alert_class.objects.issue_from_signal(**kwargs)
    if alert:
        logger.debug(
            "Alert (%s) issued from signal: %s", alert, kwargs.get("signal", None)
        )


def rescind_alert(alert_class, **kwargs):
    rescinded = alert_class.objects.rescind_from_signal(**kwargs)
    if rescinded:
        logger.debug(
            "%d alerts rescinded from signal: %s",
            rescinded[0],
            kwargs.get("signal", None),
        )


def valid_signals(signals):
    signal_set = set()
    for sig in signals:
        if isinstance(sig, str):
            try:
                sig = import_string(sig)
            except ImportError:
                pass
        if isinstance(sig, Signal):
            signal_set.add(sig)
    return signal_set


for alert, config in getattr(settings, "SLM_AUTOMATED_ALERTS", {}).items():
    try:
        alert = apps.get_model(*alert.split(".", 1))
    except LookupError:
        continue
    if alert.automated:

        def do_connect(signal_type, connection):
            for signal in valid_signals(config.get(signal_type, [])).intersection(
                valid_signals(
                    getattr(alert.objects, "SUPPORTED_SIGNALS", {}).get(signal_type, [])
                )
            ):
                signal.connect(connection)

        # signal receivers are stored as weak references, so we need to make
        # sure they don't get garbage collected
        issue = partial(issue_alert, alert_class=alert)
        rescind = partial(rescind_alert, alert_class=alert)
        receivers.append(issue)
        receivers.append(rescind)
        do_connect("issue", issue)
        do_connect("rescind", rescind)


@receiver(slm_signals.alert_issued)
def send_alert_emails(sender, alert, **kwargs):
    if alert.send_email:
        alert.send(request=kwargs.get("request", None))

    if hasattr(alert, "site") and isinstance(alert.site, Site):
        Site.objects.filter(pk=alert.site.pk).update_alert_levels()


@receiver(slm_signals.alert_cleared)
def handle_alert_cleared(sender, alert, **kwargs):
    if hasattr(alert, "site") and isinstance(alert.site, Site):
        Site.objects.filter(pk=alert.site.pk).update_alert_levels()
