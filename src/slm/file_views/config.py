import inspect
import typing as t
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from django.urls import path
from django.urls.resolvers import URLPattern
from django.utils.module_loading import import_string

from slm.defines import SiteLogFormat, SiteLogStatus


@dataclass
class Listing:
    """
    This is the interface for a file/directory listing that the template expects to render.
    """

    display: str
    """
    The name to display.
    """

    modified: t.Optional[datetime] = None
    """
    The last time this file or directory was modified.
    """

    size: t.Optional[int] = None
    """
    The size in bytes of the file if available.
    """

    is_dir: bool = False
    """
    True if this listing is a directory, False otherwise
    """

    on_disk: t.Optional[Path] = None
    """
    The path to the file or directory on disk.
    """

    def from_glob(
        pattern: t.Optional[str], filter: t.Callable[[str], bool] = lambda _: True
    ) -> t.Generator["Listing", None, None]:
        """
        Yield :class:`~slm.file_views.config.Listing` objects from a glob
        pattern.

        :param pattern: A glob pattern
        :param filter: A callable that takes the name of the file or directory
            and returns True if it should be included and False otherwise. Includes
            everything by default.
        :return: An iterable of :class:`~slm.file_views.config.Listing`
            objects.
        """
        if pattern:
            from glob import iglob

            for path_str in iglob(pattern):
                on_disk = Path(path_str)
                stat = on_disk.stat()
                if filter(on_disk.name):
                    yield Listing(
                        display=on_disk.name,
                        modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                        size=None if on_disk.is_dir() else stat.st_size,
                        is_dir=on_disk.is_dir(),
                        on_disk=on_disk,
                    )


@dataclass
class Entry:
    view: str = ""
    """
    The import path to the view function or class.
    """

    download: t.Optional[bool] = None
    """
    If true, clicking on a file will download it, otherwise it will be opened in the browser
    if it is a supported mime type.
    """

    name: t.Optional[str] = None
    """
    The name used to reverse the view. By default the name will be the path parts separated
    by __
    """

    decorator: t.Optional[t.Callable[..., t.Any]] = None
    """
    A decorator to apply to the view. For example, to require login to access this
    view set this to :func:`~django.contrib.auth.decorators.login_required`
    """

    options: t.Dict[str, t.Any] = field(default_factory=dict)
    """
    Extra kwargs to pass to path().
    """

    def urls(self, pth: Path, **kwargs) -> t.Sequence[URLPattern]:
        if self.view_callback is None:
            return []
        path_str = self.path_str(pth)
        return (
            path(
                path_str,
                self.view_callback,
                kwargs=self.kwargs(**kwargs),
                name=self.view_name(pth),
            ),
        )

    def kwargs(self, **kwargs) -> t.Dict[str, t.Any]:
        from django.conf import settings

        return {
            **self.options,
            "download": self.download
            if self.download is not None
            else getattr(settings, "SLM_FILE_VIEW_DOWNLOAD", False),
            **kwargs,
        }

    @property
    def view_callback(self) -> t.Optional[t.Callable[..., t.Any]]:
        if not self.view:
            return None
        view = import_string(self.view)
        view = view.as_view() if inspect.isclass(view) else view
        if self.decorator:
            return self.decorator(view)
        return view

    def view_name(self, pth: Path) -> str:
        return self.name or self.path_str(pth).replace("/", "__")

    @staticmethod
    def path_str(pth: Path) -> str:
        return f"{'/'.join(part for part in pth.parts if part != pth.root)}/"


@dataclass
class Directory(Entry):
    order_key: t.Sequence[str] = ("is_dir", "display")

    def urls(self, pth: Path, **kwargs) -> t.Sequence[URLPattern]:
        if self.view_callback is None:
            return []
        path_str = self.path_str(pth)
        return (
            path(
                path_str,
                self.view_callback,
                kwargs=self.kwargs(**kwargs),
                name=self.view_name(pth),
            ),
        )


@dataclass
class FileSystemDirectory(Directory):
    view: str = "slm.file_views.views.FileSystemView"
    glob: t.Optional[str] = None

    def kwargs(self, **kwargs) -> t.Dict[str, t.Any]:
        return {**super().kwargs(), "glob": self.glob, **kwargs}

    def urls(self, pth: Path, **kwargs) -> t.Sequence[URLPattern]:
        if self.view_callback is None:
            return []
        path_str = self.path_str(pth)
        return (
            path(
                path_str,
                self.view_callback,
                kwargs=self.kwargs(**kwargs),
                name=self.view_name(pth),
            ),
            path(
                f"{path_str}<str:filename>",
                self.view_callback,
                kwargs=self.kwargs(**kwargs),
                name=self.view_name(pth),
            ),
        )


@dataclass
class ArchivedSiteLogs(FileSystemDirectory):
    view: str = "slm.file_views.views.ArchivedSiteLogView"

    log_formats: t.Sequence[SiteLogFormat] = field(default_factory=list)
    log_status: t.Sequence[SiteLogStatus] = field(
        default_factory=SiteLogStatus.active_states
    )
    best_format: bool = False
    most_recent: bool = False
    non_current: bool = False

    name_len: t.Optional[int] = None
    lower_case: t.Optional[bool] = None

    def kwargs(self, **kwargs) -> t.Dict[str, t.Any]:
        return {
            **super().kwargs(),
            "log_formats": self.log_formats,
            "log_status": self.log_status,
            "best_format": self.best_format,
            "most_recent": self.most_recent,
            "non_current": self.non_current,
            "name_len": self.name_len,
            "lower_case": self.lower_case,
            **kwargs,
        }


class File(Entry):
    """
    All file types must inherit from this class.
    """

    pass


@dataclass
class _Command:
    command: str
    """
    The name of the management command that generates the file. This command
    must write the file to standard out.
    """

    args: t.List[str] = field(default_factory=list)
    """
    CLI string arguments to pass to the command.
    """


@dataclass
class GeneratedFile(File, _Command):
    """
    A view that generates a file from a management command.
    """

    view: str = "slm.file_views.views.command_output_view"
    mimetype: t.Optional[str] = None
    """
    Give an explicit mime type for the generated file.
    """

    def path_str(self, pth: Path) -> str:
        return super().path_str(pth).rstrip("/")

    def kwargs(self, **kwargs) -> t.Dict[str, t.Any]:
        return {
            **super().kwargs(),
            "command": self.command,
            "mimetype": self.mimetype,
            "args": self.args,
            **kwargs,
        }

    def urls(self, pth: Path, **kwargs) -> t.Sequence[URLPattern]:
        if self.view_callback is None:
            return []
        return (
            path(
                self.path_str(pth),
                self.view_callback,
                kwargs=self.kwargs(**kwargs),
                name=self.view_name(pth),
            ),
        )
