import fnmatch
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.db.models import (
    DateTimeField,
    F,
    Func,
    Max,
    PositiveIntegerField,
    Window,
)
from django.db.models.functions import Length, RowNumber, TruncDate
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from slm.defines import SiteLogFormat, SiteLogStatus
from slm.models import ArchivedSiteLog, ArchiveIndex, Site


@cache_page(3600 * 12, key_prefix="file_views")
class LegacyFTPView(TemplateView):
    """
    This view emulates the legacy ftp emulation at
    https://files.igs.org/pub/station/log
    and https://files.igs.org/pub/station/log_9char

    It allows access to site log text and a wild card/plain text listing
    interface if the ?list url query parameter is present.
    """

    sites = Site.objects.active()

    log_formats = [
        SiteLogFormat.LEGACY,
    ]

    lookup_field = "filename"

    DEFAULT_ORDER = ("filename",)

    order_field = {
        "N": ("filename",),
        "S": ("size",),
        "M": ("last_publish",),
        "D": ("filename",),
    }

    @property
    def content_type(self):
        if "listing.txt" in self.get_template_names():
            return "text/plain"
        return "text/html"

    def get_template_names(self):
        if "list" in self.request.GET:
            return "slm_legacy/listing.txt"
        return "slm_legacy/ftp.html"

    def get_context_data(self, log_name=None, **kwargs):
        # we use the legacy query parameter naming even though its non-standard
        # so as not to break any links out in the wild
        field_param = "N"
        reverse = False
        params = self.request.GET.get("C", None)

        if params:
            params = f"C={params}".split(";")
            if len(params) > 0:
                field_param = params[0].split("=")[-1]
                if len(params) > 1 and params[1].split("=")[-1] == "D":
                    reverse = True

        context = super().get_context_data(**kwargs)
        sites_qry = (
            self.get_queryset(**kwargs)
            .select_related("index", "index__site")
            .annotate(
                filename_len=Length("filename", output_field=PositiveIntegerField())
            )
            .order_by(*self.order_field.get(field_param, self.DEFAULT_ORDER))
        )
        if reverse:
            sites_qry = sites_qry.reverse()
        context["sites"] = sites_qry

        max_len = context["sites"].aggregate(Max("filename_len"))["filename_len__max"]

        # hardcode removal of extra _HHMMSS from filename max lengths
        max_len = max_len - 7 if max_len > 22 else max_len

        if "list" in self.request.GET and log_name:
            context["sites"] = context["sites"].filter(
                filename__iregex=fnmatch.translate(log_name)
                .rstrip(")\\Z")
                .lstrip("(?s:")
            )

        context["padding"] = " " * (24 - max_len)
        context["max_len"] = max_len
        context["name_length"] = kwargs.get("name_length", None)
        context[f"{field_param}_ordering"] = "A" if reverse else "D"
        context["download_view"] = (
            f"{':'.join(self.request.resolver_match.namespaces)}:"
            f"{self.request.resolver_match.url_name}"
        )
        return context

    def get_queryset(self, **kwargs):
        """
        Fetch the archived site logs of legacy format for the current indexes
        of our public sites. We annotate file names because the root log views
        should always show the requested canonical name of the log file, even
        if the file name in the archive is different.

        :param kwargs:
        :return:
        """
        current_indexes = (
            ArchiveIndex.objects.filter(site__in=self.sites)
            .order_by("site", "-valid_range")
            .distinct("site")
        )
        log_formats = self.log_formats
        if "log_format" in kwargs:
            log_formats = [kwargs.get("log_format")]
        return (
            ArchivedSiteLog.objects.filter(
                log_format__in=log_formats,
                index__in=current_indexes,
            )
            .annotate_filenames(
                name_len=kwargs.get("name_length", None),
                lower_case=kwargs.get("lower_case", True),
                log_format=log_formats[0],
            )
            .annotate(
                last_publish=Func(
                    "index__valid_range", function="lower", output_field=DateTimeField()
                )
            )
        )

    def get(self, request, *args, log_name=None, **kwargs):
        from slm.models import ArchivedSiteLog

        if log_name and "list" not in self.request.GET:
            try:
                log_formats = self.log_formats
                if "log_format" in kwargs:
                    log_formats = [kwargs.get("log_format")]
                archived = (
                    self.get_queryset(**kwargs)
                    .filter(
                        **{f"{self.lookup_field}__istartswith": Path(log_name).stem},
                        log_format__in=log_formats,
                    )
                    .order_by("-timestamp")
                    .first()
                )
                if not archived:
                    raise Http404()
                return FileResponse(archived.file, filename=log_name)
            except ArchivedSiteLog.DoesNotExist:
                raise Http404()

        return super().get(request, *args, log_name=log_name, **kwargs)


@cache_page(3600 * 12, key_prefix="file_views")
class LegacyFTPArchiveView(LegacyFTPView):
    sites = Site.objects.public()

    DEFAULT_ORDER = ("index__site__name", "timestamp")

    log_formats = [SiteLogFormat.LEGACY, SiteLogFormat.ASCII_9CHAR]
    lookup_field = "name"

    order_field = {
        **LegacyFTPView.order_field,
        "N": DEFAULT_ORDER,
        "D": DEFAULT_ORDER,
    }

    def get_queryset(self, **kwargs):
        """
        For archived log view we show the name at the time the log
        was in use.

        :param kwargs:
        :return:
        """
        return ArchivedSiteLog.objects.annotate(
            best_log=Window(
                expression=RowNumber(),
                partition_by=[
                    F("index__site"),
                    TruncDate("timestamp"),
                ],
                order_by=[
                    F("timestamp").desc(),
                    F("log_format").desc(),
                ],  # higher format wins
            ),
            filename=F("name"),
            last_publish=Func(
                F("index__valid_range"), function="lower", output_field=DateTimeField()
            ),
        ).filter(
            log_format__in=self.log_formats,
            best_log=1,  # prefer the best format that is available and the most recent log for each day
            index__site__in=self.sites,  # fetch only for the filtered sites
            index__valid_range__upper_inf=False,  # get only non-current logs
        )


@cache_page(3600 * 12, key_prefix="file_views")
class FinalLogView(LegacyFTPArchiveView):
    sites = Site.objects.filter(status=SiteLogStatus.FORMER)

    def get_queryset(self, **kwargs):
        """
        For archived log view we show the canonical name at the time the log
        was in use.

        :param kwargs:
        :return:
        """
        last_indexes = (
            ArchiveIndex.objects.filter(site__in=self.sites)
            .order_by("site", "-valid_range")
            .distinct("site")
        )

        return (
            ArchivedSiteLog.objects.filter(
                log_format=SiteLogFormat.LEGACY, index__in=last_indexes
            )
            .annotate(filename=F("name"))
            .annotate(
                last_publish=Func(
                    "index__valid_range", function="lower", output_field=DateTimeField()
                )
            )
            .distinct()
        )


@cache_page(3600 * 12, key_prefix="file_views")
def sinex(request, **kwargs):
    """
    Return a generated sinex file from the currently published site log data.
    """
    # Create an in-memory buffer for the command's output
    out = StringIO()
    # Call the command and redirect its output to the in-memory buffer
    call_command("generate_sinex", **kwargs, stdout=out)
    out.seek(0)
    return StreamingHttpResponse(out, content_type="text/plain")
