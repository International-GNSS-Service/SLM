"""
When transitioning site log management into an SLM you will have to import all of the
existing data. There are two primary steps involved in doing this:

1. Import the index of existing serialized point in time site logs.
2. Populate the site log fields in the database from the most recent site logs for each
   station.

This command will perform #1 and optionally call :django-admin:`head_from_index` on the
imported stations to also perform #2.

.. tip::

    Rich HTML logs of the import process will be written to:

        ``settings.SLM_LOG_DIR / import_archive.TIMESTAMP``

Logs will be parsed and errors reported, but parsing errors will not prevent logs from
being indexed.

.. warning::

    If timestamps cannot be determined for files they will not be indexed
    because each entry in the file index requires a begin and end time.
"""

import os
import re
import sys
import tarfile
import typing as t
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from dateutil.parser import ParserError
from dateutil.parser import parse as parse_datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import CommandError
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.timezone import is_naive, make_aware
from django.utils.translation import gettext as _
from django_typer.completers import complete_directory, complete_path, these_strings
from django_typer.management import TyperCommand, get_command, model_parser_completer
from django_typer.types import Traceback, Verbosity
from tqdm import tqdm
from typer import Argument, Option
from typing_extensions import Annotated

from slm.defines import SiteLogFormat, SiteLogStatus, SLMFileType
from slm.models import Agency, ArchivedSiteLog, ArchiveIndex, Site, User
from slm.parsing.legacy import SiteLogBinder, SiteLogParser
from slm.parsing.xsd import (
    SiteLogBinder as XSDSiteLogBinder,
)
from slm.parsing.xsd import (
    SiteLogParser as XSDSiteLogParser,
)

from .head_from_index import Command as HeadFromIndex


def make_aware_utc(dt: t.Union[str, datetime, date]) -> datetime:
    if not dt:
        return dt
    if isinstance(dt, str):
        dt = parse_datetime(dt, tzinfos={"UT": timezone.utc, "UTUT": timezone.utc})
    if isinstance(dt, datetime):
        if is_naive(dt):
            return make_aware(dt, timezone.utc)
    elif isinstance(dt, date):
        return datetime(month=dt.month, day=dt.day, year=dt.year, tzinfo=timezone.utc)
    return dt


def list_files(directory: Path) -> t.List[Path]:
    """
    Return a list of all files at a below the given directory path.

    :param directory: The root path to fetch files from.
    :return: A list of file paths in the directory or subdirectories
    """
    file_list = []
    for root, _1, files in os.walk(directory):
        for file in files:
            file_list.append(Path(os.path.join(root, file)))
    return file_list


@dataclass
class FileMeta:
    filename: str
    name: str
    format: SiteLogFormat
    mtime: t.Optional[int] = None
    file_date: t.Optional[datetime] = None
    prep_date: t.Optional[datetime] = None
    site: t.Optional[Site] = None
    contents: t.Optional[bytes] = field(repr=False, default=None)
    index: t.Optional[ArchiveIndex] = None
    archived_log: t.Optional[ArchivedSiteLog] = None

    # a year, but no date could be determined from the filename
    no_day: bool = True

    bound: t.Optional[SiteLogBinder] = None

    def get_param(self, section_index, field_name, null_val=None):
        if not self.bound:
            return null_val
        section = self.bound.parsed.sections.get(section_index, None)
        binding = getattr(section, "binding", {})
        if binding and field_name in binding:
            return binding.get(field_name)
        if section:
            # param may be unbound (i.e. not captured by a known name)
            params = section.get_params(field_name)
            if params:
                if len(params) == 1:
                    return params[0].value
                return [param.value for param in params]
        return null_val

    @property
    def warnings(self):
        if self.bound:
            return self.bound.parsed.warnings
        return []

    @property
    def errors(self):
        if self.bound:
            return self.bound.parsed.errors
        return []


def parse_format(fmt: str):
    if isinstance(fmt, SiteLogFormat):
        return fmt
    return SiteLogFormat(fmt)


class Command(TyperCommand):
    """
    This command will import serialized site logs into the index and the site log
    data model. Hooks are provided to derive from this class and customize parts
    of the import process. See:

        * process_filename() - To customize how log files are recognized and how
            needed information is extracted from their names
        * decode_log() - Decode log file bytes into a string.
    """

    help = _(
        "Import an archive of old site logs - creating indexes and optionally "
        "importing the latest file information into the database."
    )

    suppressed_base_arguments = {
        "version",
        "pythonpath",
        "settings",
    }

    # the file argument
    file: Path

    formats: t.List[t.Union[str, SiteLogFormat]] = list(
        set([fmt.ext for fmt in SiteLogFormat])
    )
    site_dirs: bool = False
    unresolved: t.List[t.Tuple[str, str]]
    imported: t.Set[Site]
    created: t.Set[Site]
    indexes: t.Set[ArchiveIndex]
    skipped: t.List[FileMeta]
    site_files = t.Dict[Site, t.Dict[datetime, t.List[FileMeta]]]
    head_indexes = t.Dict[Site, FileMeta]

    no_create_sites: bool = False
    set_status: t.Optional[SiteLogStatus] = None
    update_head: bool = True
    agencies: t.List[Agency] = []
    owner: t.Optional[User] = None

    logs: Path = Path("{SLM_LOG_DIR}") / "import_archive.{TIMESTAMP}"
    verbosity: int = 1
    traceback: bool = False

    log_file_tmpl = "slm/reports/file_log.html"
    log_index_tmpl = "slm/reports/index_log.html"

    # this matches fourYYMM.log and four_YYYYMMDD.log styles
    FILE_NAME_REGEX = re.compile(
        r"^((?P<four_id>[a-zA-Z\d]{4})(?P<yymm>\d{4})?|"
        r"((?P<site>[a-zA-Z\d]{4,})?\D*(?P<date_part>\d{8})?(?P<extra>.*)?))"
        r"[.](?P<ext>(log)|(sitelog)|(txt)|(xml)|(gml)|(json))$"
    )

    def process_filename(
        self, filename: str, site_name: str = "", mtime: t.Optional[int] = None
    ) -> t.Optional[FileMeta]:
        """
        Process a filename and return a FileMeta object or None if this file
        is not a log file and/or uninterpretable as a log file.

        .. note::

            Deriving import commands can override this function or the FILE_NAME_REGEX
            to customize this functions behavior.

        This will match files with .log or .txt extensions and names that have the
        following format:

            * starts with the site name (or not if site_name is passed)
            * middle characters can be any non-digit character
            * ends with a timestamp in either:
                * yyyymmdd
                * yymm
                * mmddyyyy

        .. note::

            If no day was present on the filename date stamp, jan 1 is used

        :param filename: The name of the file, including the extension.
        :param site_name: A string that might possibly be the site name and could
            be used if no site name is determinable from the filename.
        :return FileMeta or None if the filename was not interpretable
        """
        match = self.FILE_NAME_REGEX.match(filename)

        if match:
            groups = match.groupdict()
            if not (self.site_dirs and site_name):
                site_name = groups.get("site") or groups.get("four_id") or site_name
            if not site_name:
                return None
            site_name = site_name.upper()
            file_date = None
            no_day = False
            if groups["yymm"]:
                no_day = True
                year = int(groups["yymm"][:2])
                if year > 80:
                    year += 1900
                else:
                    year += 2000
                month = int(groups["yymm"][2:])
                file_date = datetime(year=year, month=month, day=1)
            elif groups["date_part"]:
                date_part_full = f"{groups['date_part']}{groups['extra'] or ''}"
                try:
                    file_date = parse_datetime(
                        date_part_full,
                        tzinfos={"UT": timezone.utc, "UTUT": timezone.utc},
                    )
                except ParserError:
                    try:
                        file_date = parse_datetime(
                            groups["date_part"],
                            tzinfos={"UT": timezone.utc, "UTUT": timezone.utc},
                        )
                    except ParserError:
                        if self.verbosity > 1:
                            self.secho(
                                _(
                                    "Unable to interpret {date_part_full} as a date "
                                    "on {filename}."
                                ).format(
                                    date_part_full=date_part_full, filename=filename
                                ),
                                fg="red",
                            )

            return FileMeta(
                filename=filename,
                name=site_name,
                mtime=mtime,
                format=SiteLogFormat(groups.get("ext", "log")),
                file_date=make_aware_utc(file_date),
                no_day=no_day,
            )

        return None

    def handle(
        self,
        archive: Annotated[
            t.Optional[Path],
            Argument(
                exists=True,
                dir_okay=True,
                help=_(
                    "The path to the archive containing the legacy site logs to "
                    "import. May be a tar file, a directory or a single site log."
                ),
                shell_complete=complete_path,
            ),
        ] = None,
        no_create_sites: Annotated[
            bool,
            Option(
                "--no-create-sites",
                help=_(
                    "Do not create sites if they do not already exist in the database."
                ),
            ),
        ] = no_create_sites,
        set_status: Annotated[
            t.Optional[SiteLogStatus],
            Option(
                metavar="STATUS",
                help=_("Set this status as the site status for imported sites."),
                parser=lambda f: SiteLogStatus(f),
                shell_complete=these_strings(
                    [str(status.label) for status in SiteLogStatus]
                ),
            ),
        ] = set_status,
        no_update_head: Annotated[
            bool,
            Option(
                "--no-update-head",
                help=_(
                    "For all indexes added at the head index for each site, import "
                    "that site log data into the database."
                ),
            ),
        ] = not update_head,
        agencies: Annotated[
            t.List[Agency],
            Option(
                "--agency",
                help=_("Assign all sites to this agency or these agencies."),
                **model_parser_completer(
                    Agency, "shortname", case_insensitive=True, help_field="name"
                ),
            ),
        ] = agencies,
        owner: Annotated[
            t.Optional[User],
            Option(
                "--owner",
                help=_("Assign all sites to this owner."),
                **model_parser_completer(
                    User, "email", case_insensitive=True, help_field="full_name"
                ),
            ),
        ] = owner,
        logs: Annotated[
            Path,
            Option(
                help=_("Write parser logs to this directory."),
                shell_complete=complete_directory,
            ),
        ] = logs,
        formats: Annotated[
            t.List[
                str
            ],  # list of SiteLogFormat's does not work for some upstream reason
            Option(
                "--format",
                metavar="FORMAT",
                help=_("Only import any site logs of the specified format(s)."),
                shell_complete=these_strings(set([fmt.ext for fmt in SiteLogFormat])),
            ),
        ] = formats,
        site_dirs: Annotated[
            bool,
            Option(
                "--site-dirs",
                help=_(
                    "Interpret the directories containing the logs as the site names."
                ),
            ),
        ] = site_dirs,
        verbosity: Verbosity = verbosity,
        traceback: Traceback = traceback,
    ):
        if not archive:
            archive = Path(
                input(_("Where is the archive? (directory or tar/zip): ")).strip()
            )
        self.archive = archive.expanduser()
        if not self.archive.exists():
            raise CommandError(
                _("{archive} does not exist!").format(archive=self.archive)
            )
        self.no_create_sites = no_create_sites
        self.set_status = set_status
        self.update_head = not no_update_head
        self.agencies = agencies
        self.owner = owner
        self.logs = Path(
            str(logs).format(
                SLM_LOG_DIR=getattr(settings, "SLM_LOG_DIR", "./"),
                TIMESTAMP=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            )
        )
        self.formats = [SiteLogFormat(fmt) for fmt in formats]
        self.site_dirs = site_dirs
        self.verbosity = verbosity
        self.traceback = traceback

        self.unresolved = []
        self.created = set()
        self.imported = set()
        self.indexes = set()
        self.skipped = []
        self.site_files = {}
        self.head_indexes = {}

        if not self.archive.exists():
            raise CommandError(_("{file} does not exist.").format(file=self.archive))

        # if SiteLogFormat.GEODESY_ML in self.formats:
        #     # TODO - only do this if necessary
        #     from slm.parsing.xsd import load_schemas

        #     load_schemas()

        if self.archive.is_file() and tarfile.is_tarfile(self.archive):
            with tarfile.open(self.archive, "r") as archive:
                with tqdm(
                    total=len(archive.getnames()),
                    desc=_("Importing"),
                    unit="logs",
                    postfix={"log": ""},
                    disable=self.verbosity != 1,
                ) as p_bar:
                    for member in archive.getmembers():
                        if not member.isfile():
                            continue

                        archive_path = Path(member.name)
                        archive_name = archive_path.name
                        p_bar.set_postfix({"log": archive_name})

                        file_meta = self.process_filename(
                            archive_name,
                            site_name=archive_path.parent.name
                            if archive_path.parent != Path(".")
                            else "",
                            mtime=member.mtime,
                        )
                        if not file_meta:
                            p_bar.update(n=1)
                            self.unresolved.append(
                                (archive_name, _("Unable to interpret filename."))
                            )
                            if self.verbosity > 1:
                                self.secho(
                                    _(
                                        "Unable to interpret {filename} as a site log."
                                    ).format(filename=archive_name),
                                    fg="red",
                                )
                            continue
                        if file_meta.format not in self.formats:
                            self.unresolved.append(
                                (
                                    archive_name,
                                    _(
                                        "Skipping {filename} because it is not one of "
                                        "{formats}."
                                    ).format(
                                        filename=archive_name, formats=self.formats
                                    ),
                                )
                            )
                            continue

                        file_meta.contents = archive.extractfile(member).read()
                        p_bar.update(n=1)
                        try:
                            self.process_file(file_meta)
                        except Exception as err:
                            if self.traceback:
                                raise err
                            self.unresolved.append((archive_name, str(err)))

        elif self.archive.is_dir():
            files = list_files(self.archive)
            with tqdm(
                total=len(files),
                desc=_("Importing"),
                unit="logs",
                postfix={"log": ""},
                disable=self.verbosity != 1,
            ) as p_bar:
                for file in files:
                    p_bar.set_postfix({"log": file.name})
                    file_meta = self.process_filename(
                        file.name,
                        site_name=file.parent.name if file.parent != Path(".") else "",
                        mtime=file.stat().st_mtime,
                    )
                    if not file_meta:
                        p_bar.update(n=1)
                        self.unresolved.append(
                            (file.name, _("Unable to interpret filename."))
                        )
                        if self.verbosity > 1:
                            self.secho(
                                _(
                                    "Unable to interpret {filename} as a site log."
                                ).format(filename=file.name),
                                fg="red",
                            )
                        continue

                    if file_meta.format not in self.formats:
                        self.unresolved.append(
                            (
                                file_meta.filename,
                                _(
                                    "Skipping {filename} because it is not one of "
                                    "{formats}."
                                ).format(filename=file.name, formats=self.formats),
                            )
                        )
                        continue

                    file_meta.contents = file.read_bytes()
                    p_bar.update(n=1)
                    try:
                        self.process_file(file_meta)
                    except Exception as err:
                        if self.traceback:
                            raise err
                        self.unresolved.append((file_meta.filename, str(err)))

        else:
            file_meta = self.process_filename(
                self.archive.name, mtime=self.archive.stat().st_mtime
            )
            if not file_meta:
                raise CommandError(
                    _(
                        "Unable to interpret {file} as either an tar archive or a site log."
                    ).format(file=self.archive)
                )
            file_meta.contents = self.archive.read_bytes()
            self.process_file(file_meta)

        if self.verbosity > 0:
            if self.unresolved:
                self.secho(
                    _("Unindexed files: {unresolved}").format(
                        unresolved=len(self.unresolved)
                    ),
                    fg="red",
                )
            if self.created:
                self.secho(
                    _("Created {sites} sites.").format(sites=len(self.created)),
                    fg="green",
                )
            if self.skipped:
                self.secho(
                    _("Skipped {skipped} files due to timestamp conflicts.").format(
                        skipped=len(self.skipped)
                    ),
                    fg="yellow",
                )
            self.secho(
                _("Indexed {count} files.").format(count=len(self.indexes)), fg="green"
            )

        with tqdm(
            total=len(self.imported),
            desc=_("Updating Site State"),
            unit="sites",
            postfix={"site": ""},
            disable=self.verbosity != 1,
        ) as p_bar:
            for site in self.imported:
                site.refresh_from_db()
                p_bar.set_postfix({"site": site.name})
                if self.verbosity > 1:
                    self.secho(
                        _("Updating {site} state.").format(site=site.name), fg="blue"
                    )
                save = False
                recent_first = ArchiveIndex.objects.filter(site=site).order_by(
                    "-valid_range"
                )
                latest = recent_first.first()
                oldest = recent_first.last()
                if site.last_publish is None or site.last_publish < latest.begin:
                    site.last_publish = latest.begin
                    save = True
                if site.last_update is None or site.last_update < site.last_publish:
                    site.last_update = site.last_publish
                    save = True
                if site.created is None or site.created < oldest.begin:
                    site.created = oldest.begin
                    save = True
                if site.join_date is None and site in self.created:
                    site.join_date = site.created.date()
                    save = True
                if self.set_status:
                    site.status = self.set_status
                    save = True
                if save:
                    site.save()
                p_bar.update(n=1)

        log = None
        if self.logs:
            sites: t.Dict[Site, t.List[FileMeta]] = {}
            for site in sorted(self.site_files.keys(), key=lambda s: s.name):
                site.refresh_from_db()
                sites[site] = []
                for dt in sorted(self.site_files[site].keys()):
                    sites[site].extend(
                        [
                            file
                            for file in sorted(
                                self.site_files[site][dt], key=lambda f: f.index.begin
                            )
                            if file.index and file.bound
                        ]
                    )
            with tqdm(
                total=len(sites),
                desc=_("Writing Logs"),
                unit="sites",
                postfix={"site": ""},
                disable=self.verbosity != 1,
            ) as p_bar:
                for site, files in sites.items():
                    for file in files:
                        parser_log = render_to_string(
                            self.log_file_tmpl,
                            {
                                "site": site,
                                "file": self.decode_log(file.contents),
                                "filename": file.filename,
                                "findings": file.bound.parsed.findings_context,
                                "format": file.archived_log.log_format
                                if file.archived_log
                                else None,
                                "SiteLogFormat": SiteLogFormat,
                            },
                        )
                        parser_log_dir = self.logs / site.name
                        os.makedirs(parser_log_dir, exist_ok=True)
                        log_file = parser_log_dir / f"{file.filename}.html"
                        if self.verbosity > 1:
                            self.secho(
                                _("Writing log {log_file}").format(log_file=log_file),
                                fg="blue",
                            )
                        with open(log_file, "wt") as log_f:
                            log_f.write(parser_log)
                    p_bar.update(n=1)
                    p_bar.set_postfix({"site": site.name})

        head_logs = None
        if self.update_head:
            head_logs = self.logs / "head" if self.logs else None
            get_command("head_from_index", HeadFromIndex)(
                self.head_indexes.keys(),
                formats=self.formats,
                no_prompt=True,
                verbosity=self.verbosity,
                logs=head_logs,
                traceback=traceback,
            )

        if self.logs:
            log_index = render_to_string(
                self.log_index_tmpl,
                {
                    "command": " ".join([Path(sys.argv[0]).name, *sys.argv[1:]]),
                    "runtime": datetime.now(),
                    "sites": sites,
                    "unresolved": self.unresolved,
                    "head_logs": (head_logs / "index.html").relative_to(self.logs),
                },
            )
            parser_log_dir = self.logs
            os.makedirs(parser_log_dir, exist_ok=True)
            log = parser_log_dir / "index.html"
            with open(log, "wt") as log_f:
                log_f.write(log_index)

        if log:
            import webbrowser

            webbrowser.open(log.resolve().as_uri())
            if self.verbosity > 0:
                return log.absolute()

    def process_file(self, file_meta: FileMeta):
        with transaction.atomic():
            site = Site.objects.filter(name__istartswith=file_meta.name[0:4]).first()

            if not site:
                if not self.no_create_sites:
                    site = Site.objects.create(
                        name=file_meta.name.upper(),
                        status=SiteLogStatus.EMPTY,
                    )
                    self.created.add(site)
                    if self.verbosity > 1:
                        self.secho(
                            _("Created site {site}.").format(site=site.name), fg="green"
                        )
                else:
                    raise CommandError(
                        _(
                            "Unable to find site for {filename} and site creation is disabled (see --create-sites)."
                        ).format(filename=file_meta.filename)
                    )

            file_meta.site = site

            self.parse_log(file_meta)

            # format may have changed after parsing, so we check again
            if file_meta.format not in self.formats:
                raise CommandError(
                    _("Skipping {filename} because it is not one of {formats}.").format(
                        filename=file_meta.filename, formats=self.formats
                    )
                )

            if site in self.created:
                name_changed = False
                if site.name != file_meta.name.upper() and len(site.name) < len(
                    file_meta.name
                ):
                    site.name = file_meta.name.upper()
                    site.save()
                    name_changed = True

                if (
                    file_meta.bound.parsed.site_name
                    and len(file_meta.bound.parsed.site_name) > len(site.name)
                    and file_meta.bound.parsed.site_name.upper().startswith(site.name)
                ):
                    # sometimes the fullname is only in the file! here we use it if
                    # its prefixed by the site name and is longer
                    site.name = file_meta.bound.parsed.site_name.upper()
                    site.save()
                    name_changed = True

                if name_changed:
                    for index in ArchiveIndex.objects.filter(site=site):
                        for file in index.files.all():
                            file.update_directory()

            self.imported.add(site)

            log_time = self.determine_time(file_meta)
            if not log_time:
                raise CommandError(
                    _("Unable to determine timestamp for {filename}.").format(
                        filename=file_meta.filename
                    )
                )

            self.site_files.setdefault(site, {})
            self.site_files[site].setdefault(log_time, [])
            self.site_files[site][log_time].append(file_meta)

            if site.join_date is None or site.join_date > log_time.date():
                site.join_date = log_time.date()

            if site.created is None or site.created > log_time:
                site.created = log_time

            if self.owner:
                site.owner = self.owner

            if self.agencies:
                site.agencies.set(self.agencies)

            site.save()

            index = ArchiveIndex.objects.insert_index(site=site, begin=log_time)
            file_meta.index = index
            self.indexes.add(index)
            if not index.end:
                self.head_indexes[site] = file_meta

            if any(
                [
                    meta.mtime > file_meta.mtime
                    for meta in self.site_files[site][log_time]
                    if meta is not file_meta and meta.format is file_meta.format
                ]
            ):
                # only save the most recently modified site log of the given format
                # at the given time
                self.skipped.append(file_meta)
                return

            file_meta.archived_log = ArchivedSiteLog.objects.get_or_create(
                index=index,
                log_format=file_meta.format,
                defaults={
                    "site": site,
                    "name": file_meta.filename,
                    "file_type": SLMFileType.SITE_LOG,
                    "file": ContentFile(file_meta.contents, name=file_meta.filename),
                },
            )[0]

            if self.verbosity > 1:
                self.secho(
                    _("Added index {index_file}").format(
                        index_file=str(file_meta.archived_log)
                    ),
                    fg="blue",
                )

    def parse_log(self, file_meta: FileMeta):
        """
        Parse the log file and attach the binder instance to file_meta.bound. Optionally,
        if configured write the parsing log html file out to the specified directory.
        """

        log_str = self.decode_log(file_meta.contents)
        if file_meta.format is SiteLogFormat.GEODESY_ML:
            file_meta.bound = XSDSiteLogBinder(
                XSDSiteLogParser(log_str, site_name=file_meta.site.name)
            )
        else:
            file_meta.bound = SiteLogBinder(
                SiteLogParser(log_str, site_name=file_meta.site.name)
            )

        prep_time = file_meta.get_param((0, None, None), "date_prepared")
        if not prep_time:
            prep_time = file_meta.get_param((0, None, None), "date")
        if prep_time:
            try:
                prep_date = make_aware_utc(prep_time)
            except ParserError:
                prep_date = None

            file_meta.prep_date = prep_date
        elif file_meta.format in [SiteLogFormat.LEGACY, SiteLogFormat.ASCII_9CHAR]:
            # sometimes you see files in the wild with site form subsections
            def get_subsection_date(idx: int):
                return make_aware_utc(
                    file_meta.get_param((0, idx, None), "date_prepared")
                    or file_meta.get_param((0, idx, None), "date")
                )

            prepared_dates = [get_subsection_date(0), get_subsection_date(1)]
            while prepared_dates[-1]:
                prepared_dates.append(get_subsection_date(len(prepared_dates)))
            prepared_dates = sorted([dt for dt in prepared_dates if dt])
            if prepared_dates:
                file_meta.prep_date = prepared_dates[-1]

        if file_meta.format is SiteLogFormat.LEGACY:
            if file_meta.get_param((1, None, None), "nine_character_id"):
                file_meta.format = SiteLogFormat.ASCII_9CHAR

    def decode_log(self, contents: t.Union[bytes, str]) -> str:
        """
        Decode the contents of a log file. The site log format has been around since the
        early 1990s so we may encounter exotic encodings.

        :param contents: The bytes of the log file contents.
        :return a decoded string of the contents
        """
        if isinstance(contents, str):
            return contents
        try:
            return contents.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return contents.decode("ascii")
            except UnicodeDecodeError:
                return contents.decode("latin")

    def determine_time(self, file_meta: FileMeta) -> datetime:
        """
        Determine the timestamp to use for the file:

            * Use the timestamp from the file if it is higher resolution than a date.
            * If no day was given on the file timestamp use the prep_date if it
              agrees with the file timestamp month and year.
            * Use prepared by date in the log if it is given and no timestamp could be
              determined from the file name.
        """

        log_time = None
        if file_meta.file_date:
            log_time = file_meta.file_date
            if log_time.hour or log_time.minute or log_time.second:
                return log_time

        if file_meta.prep_date:
            if not log_time:
                return file_meta.prep_date
            elif (
                file_meta.prep_date.month == log_time.month
                and file_meta.prep_date.year == log_time.year
                and file_meta.no_day
            ):
                # use the prep date if it agrees with a lower
                # resolution log_date (i.e. no day - old style)
                log_time = file_meta.prep_date

        return log_time
