from django.dispatch import Signal
from django.conf import settings
from django.utils.module_loading import import_string
from django.apps import apps
import logging
from functools import partial

logger = logging.getLogger(f'{__name__}.alert_check')


def alert_check(alert_class, **kwargs):
    alert_class.objects.from_signal(**kwargs)


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


for alert, config in getattr(settings, 'SLM_AUTOMATED_ALERTS', {}).items():
    try:
        alert = apps.get_model(*alert.split('.', 1))
    except LookupError:
        continue
    if alert.automated:
        for signal in valid_signals(config.get('signals', [])).intersection(
            valid_signals(getattr(alert.objects, 'SUPPORTED_SIGNALS', []))
        ):
            signal.connect(partial(alert_check, alert_class=alert))
