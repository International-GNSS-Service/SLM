import csv
import fnmatch
import mimetypes
import typing as t
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.db.models import DateTimeField, F, Func, Max, PositiveIntegerField, Q, Value
from django.db.models.functions import Length
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    JsonResponse,
)
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from slm.defines import SiteLogFormat, SiteLogStatus
from slm.models import ArchivedSiteLog, Site

from .config import Listing


def guess_mimetype(pth: t.Union[Path, str]) -> str:
    return (
        (
            mimetypes.guess_type(pth.name if isinstance(pth, Path) else pth)[0]
            or "text/plain"
        )
        .split(";")[0]
        .strip()
        .lower()
    )


def is_browser_renderable(pth: t.Union[Path, str]) -> bool:
    """
    Return True if the given MIME type is typically renderable directly in browsers.
    """
    mime_type = guess_mimetype(pth)
    return mime_type.startswith("text") or mime_type in getattr(
        settings, "BROWSER_RENDERABLE_MIMETYPES", {}
    )


def file_cache_key(path: Path, property: t.Optional[str] = None) -> str:
    key = f"file_views:{{property}}:{path.as_posix()}"
    if property:
        return key.format(property=property)
    return key


class FileSystemView(TemplateView):
    """
    A base file system view that renders file system artifacts.
    """

    template_name = "slm/file_views/listing.html"

    builtin_listings: t.Sequence[Listing] = []

    def get_filter_patterns(self, filename=None, **_) -> t.List[str]:
        """
        Return a list of glob patterns to filter entries by from the request.

        Subclasses may override this to fetch the patterns differently or disable
        filtering:

        :param kwargs: The kwargs passed to the view.
        :return: A list of glob patterns or an empty list if no filtering should be
            done.
        """
        matches = self.request.GET.getlist("match", [])
        if filename:
            matches.append(filename)
        return filename

    def filter_listings(
        self, listings: t.Iterable[Listing], patterns: t.List[str]
    ) -> t.Generator[Listing, None, None]:
        if patterns:
            for listing in listings:
                if any(fnmatch.fnmatch(listing.display, p) for p in patterns):
                    yield listing
                    continue
        else:
            yield from listings

    def translate_order_key(self, key: str) -> t.Optional[str]:
        """
        This hook gives subclasses a chance to swap out ordering attribute keys. You may also return
        a falsey value for a key to remove it from the ordering tuple.

        :param key: The key to translate
        :return: the key that should be used
        """
        return key

    def order_listing(
        self,
        listings: t.Iterable[Listing],
        order_column: str,
        order_key: t.Sequence[str] = ("is_dir", "display"),
        reverse: bool = False,
        **_,
    ) -> t.Tuple[t.Iterable[Listing], int]:
        """
        Apply configured ordering to the listings.

        :param listings: An iterable of :class:`~slm.file_views.config.Listing`
            objects to order
        :param order_column: The column key to order on
        :param order_key: A default :class:`~slm.file_views.config.Listing`
            attribute tuple to order by.
        :param reverse: True if the ordering should be reversed, false otherwise
        :param kwargs: Other named arguments passed to the view
        :return: A 2-tuple where the first element is an iterable of ordered
            :class:`~slm.file_views.config.Listing` objects and the second element is the
            max length of all display strings
        """
        keys = tuple(key for key in self.order_keys(order_column, order_key) if key)
        max_len = 0
        if keys:

            def key_func(listing: Listing) -> t.Any:
                nonlocal max_len
                max_len = ((ln := len(listing.display)) > max_len and ln) or max_len
                return max_len

            return sorted(listings, key=key_func, reverse=reverse), max_len
        return reversed(listings) if reversed else listings, max(
            listings, key=lambda listing: listing.display
        )

    def order_keys(
        self, order_column: str, order_key: t.Sequence[str] = ("is_dir", "display"), **_
    ) -> t.Generator[str, None, None]:
        for key in {"N": order_key, "S": ("size",), "M": ("modified",)}.get(
            order_column, order_key
        ):
            yield self.translate_order_key(key)

    def get_context_data(self, filename=None, **kwargs):
        # we use the legacy query parameter naming even though its non-standard
        # so as not to break any links out in the wild
        order_column = "N"
        reverse = False
        params = self.request.GET.get("C", None)
        patterns = self.get_filter_patterns(**kwargs)
        path = Path(self.request.path)
        builtins = []
        for listing in self.filter_listings(
            (*self.builtin_listings, *kwargs.get("listings", [])), patterns=patterns
        ):
            if listing.size is None and not listing.is_dir:
                key = file_cache_key(path / listing.display)
                listing.size = cache.get(key.format(property="size"), None)
                listing.modified = cache.get(key.format(property="modified"), None)
            builtins.append(listing)
        self.builtin_listings = builtins

        if params:
            params = f"C={params}".split(";")
            if len(params) > 0:
                order_column = params[0].split("=")[-1]
                if len(params) > 1 and params[1].split("=")[-1] == "D":
                    reverse = True

        listings, max_len = self.order_listing(
            (
                *self.builtin_listings,
                *Listing.from_glob(
                    kwargs.get("glob", None),
                    filter=lambda name: any(
                        fnmatch(name, pattern) for pattern in patterns
                    ),
                ),
            ),
            order_column=order_column,
            order_key=kwargs.get("order_key", ("is_dir", "display")),
            reverse=reverse,
            **{param: value for param, value in kwargs.items() if param != "listings"},
        )
        return {
            **kwargs,
            **super().get_context_data(filename=filename, **kwargs),
            "order_column": order_column,
            "reverse": reverse,
            f"{order_column}_ordering": "A" if reverse else "D",
            "patterns": patterns,
            "listings": listings,
            "max_len": max_len,
            "parent": path.parent if path and path.parent != Path("/") else None,
        }

    def render_to_response(self, context, **kwargs):
        """Custom rendering based on content type"""
        accept = self.request.META.get("HTTP_ACCEPT", "")

        if "json" in accept or "json" in self.request.GET:
            return self.render_json_response(context, **kwargs)
        elif "text/csv" in accept or "csv" in self.request.GET:
            return self.render_csv_response(context, **kwargs)
        elif (
            "text/plain" in accept
            or "txt" in self.request.GET
            or "list" in self.request.GET
        ):
            return self.render_txt_response(context, **kwargs)

        return super().render_to_response(context, **kwargs)

    def render_json_response(self, context, **_):
        return JsonResponse(
            [
                {
                    "name": listing.display,
                    "modified": listing.modified.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%MZ"
                    ),
                    "size": listing.size,
                }
                for listing in context["listings"]
            ]
        )

    def render_csv_response(self, context):
        response = HttpResponse(content_type="text/csv")
        writer = csv.writer(response)
        writer.writerow(["Name", "Modified", "Size"])
        for listing in context["listings"]:
            writer.writerow(
                [
                    listing.display,
                    listing.modified.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%MZ"
                    ),
                    listing.size,
                ]
            )
        return response

    def render_txt_response(self, context):
        lines = [
            f"{listing.display}{' ' * (context['max_len'] - len(listing.display))} {listing.modified.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}  {listing.size or '-----'}"
            for listing in context["listings"]
        ]
        return HttpResponse("\n".join(lines), content_type="text/plain")

    def get(self, request, *args, filename=None, **kwargs):
        if filename:
            context = self.get_context_data(**kwargs)
            found = None
            listing: Listing
            for listing in context.get("listings", []):
                if listing.display == filename:
                    found = listing
                    break
            if not found:
                raise Http404()
            return FileResponse(
                listing.on_disk,
                as_attachment=context.get("download", False)
                or not is_browser_renderable(listing.display),
                filename=listing.display,
            )
        return super().get(request, *args, filename=filename, **kwargs)


@method_decorator(cache_page(3600 * 12, key_prefix="file_views"), name="dispatch")
class ArchivedSiteLogView(FileSystemView):
    """
    This view renders a file listing from the site log archive index based on
    configured parameters. The default tempates render the view as an FTP over HTTP
    interace similar to the page at https://files.igs.org/pub/station/log

    It allows access to site log text and a wild card/plain text listing
    interface if the ?list url query parameter is present.

    File list views are cached in the default cache for 12 hours, or until the
    cache is cleared by a publish event.
    """

    sites = Site.objects.public()

    log_formats: t.Sequence[SiteLogFormat] = []
    log_status: t.Sequence[SiteLogStatus] = SiteLogStatus.active_states()
    best_format: bool = False
    most_recent: bool = False
    non_current: bool = False
    name_len: t.Optional[int] = None
    lower_case: t.Optional[bool] = None

    lookup_field = "display"

    def translate_order_key(self, key: str) -> str:
        return {
            "display": self.lookup_field,
            "is_dir": "is_dir" if self.builtin_listings else None,
        }.get(key, super().translate_order_key(key))

    def get_context_data(self, filename=None, **kwargs):
        context = super().get_context_data(**kwargs)
        listings = self.get_queryset(**kwargs)
        if patterns := context.get("patterns", []):
            pattern_filter = Q()
            pattern_key = f"{self.translate_order_key('display')}__iregex"
            for pattern in patterns:
                pattern_filter |= Q(
                    **{
                        pattern_key: fnmatch.translate(pattern)
                        .rstrip(")\\Z")
                        .lstrip("(?s:")
                    }
                )
            listings = listings.filter(pattern_filter)

        context["download"] = kwargs.get(
            "download", getattr(settings, "SLM_FILE_VIEW_DOWNLOAD", False)
        )
        order_column = context.get("order_column", "N")
        order_key = context.get("order_key", ("is_dir", "display"))
        if parent_listings := context.get("listings", []):
            context["listings"], context["max_len"] = self.order_listing(
                (*parent_listings, *listings.distinct()),
                order_column=order_column,
                order_key=order_key,
                reverse=context.get("reverse", False),
                **kwargs,
            )
        else:
            # if we have no external listings we can use the database to do all of the ordering
            listings = listings.order_by(
                *(key for key in self.order_keys(order_column, order_key) if key)
            )
            if context["reverse"]:
                listings = listings.reverse()
            context["listings"] = listings.distinct()
            context["max_len"] = max(
                listings.aggregate(Max("display_len"))["display_len__max"],
                context.get("max_len", 0),
            )

        return context

    def get_queryset(
        self,
        log_formats=log_formats,
        log_status=log_status,
        best_format=best_format,
        most_recent=most_recent,
        non_current=non_current,
        name_len=name_len,
        lower_case=lower_case,
        **_,
    ):
        """
        Fetch the archived site logs of legacy format for the current indexes
        of our public sites. We annotate file names because the root log views
        should always show the requested canonical name of the log file, even
        if the file name in the archive is different.

        :param log_formats: Restrict logs to these formats
        :param log_status: Restrict logs to sites in these status states.
        :param best_format: Include the highest ranking format at each timestamp
        :param most_recent: Only include the most recent log for each site
        :param non_current: Only include archived logs that are no longer current
        :param name_len: Normalize site log names to using this many characters of the site name
        :param lower_case: Normalize site log names to lower or upper case if True or False
        :return: A queryset holding :class:`~slm.models.ArchivedSiteLog` objects matching the
            parameters.
        """
        fltr = Q(index__site__in=self.kwargs.get("sites", self.sites))

        if log_status:
            fltr &= Q(index__site__status__in=log_status)
        if log_formats:
            fltr &= Q(log_format__in=log_formats)

        qry = ArchivedSiteLog.objects.filter(fltr)

        if best_format:
            qry = qry.best_format()

        if most_recent:
            qry = qry.most_recent()

        if non_current:
            # we do it this way because in cases where the latest log has multiple indexes
            # on the same day the last same day index will appear in the results - if we
            # exclude the last  indexes in the same query it breaks
            # the windowing exclusion of older same day logs for that latest index date
            qry = ArchivedSiteLog.objects.filter(
                pk__in=qry, index__valid_range__upper_inf=False
            )

        if name_len is not None or lower_case is not None:
            self.lookup_field = "display"
            qry = qry.annotate_filenames(
                name_length=name_len or None,
                lower_case=lower_case,
                field_name="display",
            )
        else:
            self.lookup_field = "name"
            qry = qry.annotate(display=F("name"))

        return qry.annotate(
            modified=Func(
                "index__valid_range", function="lower", output_field=DateTimeField()
            ),
            is_dir=Value(False),
            display_len=Length("display", output_field=PositiveIntegerField()),
        ).select_related("index", "index__site")

    def get(self, request, *args, filename=None, **kwargs):
        from slm.models import ArchivedSiteLog

        if filename:
            try:
                archived = (
                    self.get_queryset(**kwargs)
                    .filter(**{f"{self.lookup_field}__iexact": filename})
                    .order_by("-timestamp")
                    .first()
                )
                if not archived:
                    raise Http404()
                return FileResponse(
                    archived.file,
                    filename=filename,
                    as_attachment=kwargs.get("download", False),
                )
            except ArchivedSiteLog.DoesNotExist:
                raise Http404()

        return super().get(request, *args, filename=filename, **kwargs)


@cache_page(3600 * 12, key_prefix="file_views")
def command_output_view(
    request,
    command: str,
    download: bool = False,
    mimetype: t.Optional[str] = None,
    **kwargs,
):
    """
    Return a generated sinex file from the currently published site log data.
    """
    out = StringIO()
    call_command(command, *kwargs.pop("args", []), **kwargs, stdout=out)
    out.seek(0)
    contents = out.getvalue()
    path = Path(request.path)
    response = HttpResponse(
        content=contents, content_type=mimetype or guess_mimetype(path)
    )
    key = file_cache_key(path)
    cache.set(key.format(property="size"), len(response.content), timeout=3600 * 12)
    cache.set(
        key.format(property="modified"), datetime.now(timezone.utc), timeout=3600 * 12
    )
    if download:
        response["Content-Disposition"] = f'attachment; filename="{path.name}"'
    return response
