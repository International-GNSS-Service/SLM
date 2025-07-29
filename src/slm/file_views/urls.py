from django.conf import settings
from django.urls import path

from slm.defines import SiteLogFormat
from slm.file_views.views import (
    FinalLogView,
    LegacyFTPArchiveView,
    LegacyFTPView,
    sinex,
)

SLM_INCLUDE = True

app_name = "slm_file_views"

urlpatterns = []

for list_file_type in getattr(settings, "SLM_FILE_VIEW_FORMATS", []):
    list_file_type = SiteLogFormat(list_file_type)
    urlpatterns.extend(
        [
            path(
                f"files/{list_file_type.ext}/",
                LegacyFTPView.as_view(),
                kwargs={"log_format": list_file_type},
                name=f"{list_file_type.ext}_files",
            ),
            path(
                f"files/{list_file_type.ext}/<str:log_name>",
                LegacyFTPView.as_view(),
                kwargs={"log_format": list_file_type},
                name=f"{list_file_type.ext}_files",
            ),
        ]
    )

if file_type_ranking := getattr(settings, "SLM_ARCHIVE_FORMAT_RANKING", None):
    (
        path(
            "archive/",
            LegacyFTPArchiveView.as_view(),
            name="archive",
        ),
    )
    (
        path(
            "archive/<str:log_name>",
            LegacyFTPArchiveView.as_view(),
            name="archive",
        ),
    )
    (path("final/", FinalLogView.as_view(), name="final"),)
    path(
        "final/<str:log_name>",
        FinalLogView.as_view(),
        name="final",
    )

if snx_name := getattr(settings, "SLM_SINEX_FILENAME", None):
    urlpatterns.append(path(f"files/{snx_name}", sinex, name="sinex"))
