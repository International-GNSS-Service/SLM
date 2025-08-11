import typing as t
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import path

from .config import Entry, File, Listing
from .views import FileSystemView

SLM_INCLUDE = True

app_name = "slm_file_views"

urlpatterns = []

Branch = t.Sequence[t.Union[t.Tuple[str, t.Union[Entry, "Branch"]]]]


def add_paths(url_path: Path, entries: Branch):
    listings = []
    for entry in entries:
        try:
            pth, entries = entry
        except (TypeError, ValueError) as err:
            raise ImproperlyConfigured(
                "Setting SLM_FILE_VIEW_STRUCTURE must contain sequences of (str, Entry) tuples."
            ) from err
        listings.append(Listing(pth, is_dir=not isinstance(entries, File)))
        if isinstance(entries, Entry):
            urlpatterns.extend(entries.urls(url_path / pth))
        else:
            add_paths(url_path / pth, entries)

    urlpatterns.append(
        path(
            Entry.path_str(url_path),
            FileSystemView.as_view(),
            kwargs={"path": url_path, "listings": listings},
        )
    )


add_paths(
    Path("/") / getattr(settings, "SLM_FILE_VIEW_ROOT", {}),
    (getattr(settings, "SLM_FILE_VIEW_STRUCTURE", []) or []),
)
