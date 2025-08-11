from pathlib import Path

from slm.defines import SiteLogFormat, SiteLogStatus
from slm.file_views.config import ArchivedSiteLogs, GeneratedFile
from slm.settings import env as settings_environment
from slm.settings import get_setting

env = settings_environment()

SLM_SINEX_FILENAME = env(
    "SLM_SINEX_FILENAME",
    str,
    default=get_setting(
        "SLM_SINEX_FILENAME",
        get_setting("SLM_ORG_NAME", "stations").lower().replace(" ", "_"),
    ),
)
if SLM_SINEX_FILENAME and "." not in SLM_SINEX_FILENAME:
    SLM_SINEX_FILENAME = f"{SLM_SINEX_FILENAME}.snx"

SLM_FILE_VIEW_STRUCTURE = get_setting(
    "SLM_FILE_VIEW_STRUCTURE",
    [
        (
            "archive",
            ArchivedSiteLogs(
                order_key=("index__site__name", "timestamp"),
                best_format=True,
                non_current=True,
            ),
        ),
        (
            "current",
            [
                (
                    "log",
                    ArchivedSiteLogs(
                        most_recent=True,
                        best_format=True,
                        log_formats={SiteLogFormat.LEGACY, SiteLogFormat.ASCII_9CHAR},
                    ),
                ),
                (
                    "xml",
                    ArchivedSiteLogs(
                        most_recent=True,
                        best_format=True,
                        log_formats={SiteLogFormat.GEODESY_ML},
                    ),
                ),
            ],
        ),
        (
            "former",
            ArchivedSiteLogs(
                best_format=True,
                most_recent=True,
                log_status=[SiteLogStatus.FORMER],
                log_formats={SiteLogFormat.LEGACY, SiteLogFormat.ASCII_9CHAR},
            ),
        ),
        (SLM_SINEX_FILENAME, GeneratedFile("generate_sinex", mimetype="text/plain"))
        if SLM_SINEX_FILENAME
        else None,
    ],
)

# should clicking the file links in the file view download the file or open it in the browser?
SLM_FILE_VIEW_DOWNLOAD = env(
    "SLM_FILE_VIEW_DOWNLOAD", bool, default=get_setting("SLM_FILE_VIEW_DOWNLOAD", False)
)

SLM_FILE_VIEW_ROOT = Path(
    env(
        "SLM_FILE_VIEW_ROOT",
        str,
        default=get_setting("SLM_FILE_VIEW_ROOT", Path("files")),
    )
)


BROWSER_RENDERABLE_MIMETYPES = get_setting(
    "BROWSER_RENDERABLE_MIMETYPES",
    {
        "text/html",
        "application/xhtml+xml",
        "text/css",
        "text/javascript",
        "application/javascript",
        "application/ecmascript",
        "text/ecmascript",
        "image/apng",
        "image/avif",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/svg+xml",
        "image/webp",
        "image/bmp",
        "image/x-icon",
        "image/vnd.microsoft.icon",
        "audio/midi",
        "audio/x-midi",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
        "audio/webm",
        "audio/aac",
        "video/mp4",
        "video/mpeg",
        "video/ogg",
        "video/webm",
        "video/x-msvideo",
        "video/quicktime",
        "application/xml",
        "text/xml",
        "application/rss+xml",
        "application/atom+xml",
        "application/pdf",
        "text/plain",
    },
)
