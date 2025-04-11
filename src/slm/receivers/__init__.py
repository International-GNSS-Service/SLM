_registered = False


def register():
    global _registered
    if not _registered:
        # the order of these imports is important, index receivers must happen
        # before alert receivers
        from slm.receivers import alerts, cleanup, event_loggers, index

        _registered = event_loggers and cleanup and index and alerts
