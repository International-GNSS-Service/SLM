_registered = False


def register():
    global _registered
    if not _registered:
        # the order of these imports is important, index receivers must happen
        # before alert receivers
        from slm.receivers import (
            alerts,
            cache,
            cleanup,
            event_loggers,
            index,
            migration,
        )

        _registered = (
            event_loggers and cleanup and index and alerts and migration and cache
        )
