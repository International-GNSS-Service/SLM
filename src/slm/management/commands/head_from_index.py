"""
If your site log file index is more current than the database state
(i.e. you've run :django-admin:`import_archive`), you may run this command to pull data
from the most recent indexed files into the database.

.. tip::

    By default, rich HTML logs of the import process will be written to:

        ``settings.SLM_LOG_DIR / head_from_index.TIMESTAMP``

    ImportAlerts will also be issued for any errors flagged during import. When,
    appropriate validation flags will be attached to site log fields. This allows you
    to manually clean up any import errors through the web interface after the process
    completes.
"""

import inspect
import os
import sys
import typing as t
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import DatabaseError, models, transaction
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django_typer.completers import complete_directory, these_strings
from django_typer.management import TyperCommand, model_parser_completer
from django_typer.types import Traceback, Verbosity
from tqdm import tqdm
from typer import Argument, Option
from typing_extensions import Annotated

from slm.defines import AlertLevel, SiteLogFormat, SiteLogStatus
from slm.models import ArchivedSiteLog, ArchiveIndex, ImportAlert, Site
from slm.models.sitelog import (
    SiteAntenna,
    SiteCollocation,
    SiteForm,
    SiteFrequencyStandard,
    SiteHumiditySensor,
    SiteIdentification,
    SiteLocalEpisodicEffects,
    SiteLocation,
    SiteMoreInformation,
    SiteMultiPathSources,
    SiteOperationalContact,
    SiteOtherInstrumentation,
    SitePressureSensor,
    SiteRadioInterferences,
    SiteReceiver,
    SiteResponsibleAgency,
    SiteSection,
    SiteSignalObstructions,
    SiteSubSection,
    SiteSurveyedLocalTies,
    SiteTemperatureSensor,
    SiteWaterVaporRadiometer,
)
from slm.parsing import BaseBinder, Error, Warn


@dataclass
class ImportRecord:
    index: ArchiveIndex
    file: t.Optional[ArchivedSiteLog] = None
    bound: t.Optional[BaseBinder] = None
    alert: t.Optional[ImportAlert] = None
    exception: t.Optional[str] = None
    failed: str = ""  # the reason!


class Command(TyperCommand):
    help = _("Update the head state of each site from the most recent index.")
    suppressed_base_arguments = {
        "version",
        "pythonpath",
        "settings",
    }

    sites: t.Sequence[Site]
    clean: bool = True
    prompt: bool = True
    logs: Path = Path("{SLM_LOG_DIR}") / "head_from_index.{TIMESTAMP}"
    verbosity = 1

    indexes: t.Sequence[ArchiveIndex]

    formats: t.List[t.Union[str, SiteLogFormat]] = ["log"]
    # list(
    #     set([fmt.ext for fmt in SiteLogFormat])
    # )
    unsupported = [SiteLogFormat.GEODESY_ML, SiteLogFormat.JSON]

    imports: t.List[ImportRecord]
    failed_imports: t.List[ImportRecord]
    warnings: int
    total_warnings: int
    errors: int
    total_errors: int

    log_file_tmpl = "slm/reports/file_log.html"
    log_index_tmpl = "slm/reports/head_log.html"

    SECTION_MODELS = {
        0: SiteForm,
        1: SiteIdentification,
        2: SiteLocation,
        3: SiteReceiver,
        4: SiteAntenna,
        5: SiteSurveyedLocalTies,
        6: SiteFrequencyStandard,
        7: SiteCollocation,
        (8, 1): SiteHumiditySensor,
        (8, 2): SitePressureSensor,
        (8, 3): SiteTemperatureSensor,
        (8, 4): SiteWaterVaporRadiometer,
        (8, 5): SiteOtherInstrumentation,
        (9, 1): SiteRadioInterferences,
        (9, 2): SiteMultiPathSources,
        (9, 3): SiteSignalObstructions,
        10: SiteLocalEpisodicEffects,
        11: SiteOperationalContact,
        12: SiteResponsibleAgency,
        13: SiteMoreInformation,
    }

    def yes(self, ipt):
        return ipt.lower() in {"y", "yes", "true", "continue"}

    def handle(
        self,
        sites: Annotated[
            t.Optional[t.List[Site]],
            Argument(
                **model_parser_completer(Site, "name"),
                help=_("The sites (by name) to update. (all active sites by default)"),
            ),
        ] = None,
        no_prompt: Annotated[
            bool, Option("--no-prompt", help=_("Do not ask before proceeding."))
        ] = not prompt,
        logs: Annotated[
            Path,
            Option(
                help=_(
                    "Write logs to this directory. No logs will be written by default."
                ),
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
                help=_(
                    "Only import state from these specified format(s) (in preference order)."
                ),
                shell_complete=these_strings(set([fmt.ext for fmt in SiteLogFormat])),
            ),
        ] = formats,
        verbosity: Verbosity = verbosity,
        traceback: Traceback = False,
    ):
        self.sites = sites or list(Site.objects.active())
        self.prompt = not no_prompt

        if self.prompt and not self.yes(
            input(
                _(
                    "This will clear and re-import data from the serialized archive for "
                    "{stations} stations. This cannot be undone. Continue? (y/N): "
                ).format(stations=len(sites))
            )
        ):
            return

        self.logs = Path(
            str(logs).format(
                SLM_LOG_DIR=getattr(settings, "SLM_LOG_DIR", "./"),
                TIMESTAMP=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            )
        )
        self.verbosity = verbosity
        self.traceback = traceback
        self.formats = [SiteLogFormat(fmt) for fmt in formats]
        for unsupported in self.unsupported:
            if unsupported in self.formats:
                self.secho(
                    _("{format} imports are not yet supported").format(
                        format=unsupported
                    ),
                    fg="yellow",
                )
                self.formats.remove(unsupported)
        self.warnings = 0
        self.total_warnings = 0
        self.errors = 0
        self.total_errors = 0

        if SiteLogFormat.GEODESY_ML in self.formats:
            from slm.parsing.xsd import load_schemas

            load_schemas()

        self.imports = []
        self.failed_imports = []

        self.indexes = (
            ArchiveIndex.objects.filter(
                site__in=self.sites, valid_range__upper_inf=True
            )
            .order_by("site", "-valid_range")
            .distinct("site")
        )

        with tqdm(
            total=self.indexes.count(),
            desc=_("Updating Head"),
            unit="sites",
            postfix={"site": ""},
            disable=self.verbosity != 1,
        ) as p_bar:
            for index in self.indexes:
                p_bar.set_postfix({"site": index.site.name})
                try:
                    record = ImportRecord(index=index)
                    if self.update_head(record):
                        self.imports.append(record)
                    else:
                        self.failed_imports.append(record)
                        ImportAlert.objects.update_or_create(
                            site=index.site,
                            defaults={
                                "level": AlertLevel.ERROR,
                                "header": _("Import from index failed."),
                                "detail": record.failed,
                            },
                        )
                except Exception as err:
                    if self.traceback:
                        raise err

                    import traceback

                    record.exception = traceback.format_exc()
                    record.failed = f"{type(err)}: {str(err)}"
                    self.failed_imports.append(record)
                    ImportAlert.objects.update_or_create(
                        site=index.site,
                        defaults={
                            "level": AlertLevel.ERROR,
                            "header": _("Import from index failed."),
                            "detail": record.failed,
                        },
                    )
                p_bar.update(n=1)

        if self.verbosity >= 1:
            if self.imports:
                self.secho(
                    _(
                        "Imported data from {stations} serialized station archives."
                    ).format(stations=len(self.imports)),
                    fg="green",
                )
            if self.warnings:
                self.secho(
                    _("{warnings} station imports have warnings.").format(
                        warnings=self.warnings
                    ),
                    fg="yellow",
                )
            if self.errors:
                self.secho(
                    _("{errors} station imports have errors.").format(
                        errors=self.errors
                    ),
                    fg="red",
                )
            if self.failed_imports:
                self.secho(
                    _(
                        "Failed to import data from {stations} serialized station archives."
                    ).format(stations=len(self.failed_imports)),
                    fg="red",
                )

        if self.logs:
            os.makedirs(self.logs, exist_ok=True)
            with tqdm(
                total=len(self.imports) + len(self.failed_imports),
                desc=_("Writing logs"),
                unit="station",
                postfix={"station": ""},
                disable=self.verbosity != 1,
            ) as p_bar:
                for record in [*self.imports, *self.failed_imports]:
                    p_bar.set_postfix({"station": record.index.site.name})
                    file_log = render_to_string(
                        self.log_file_tmpl,
                        {
                            "site": record.index.site,
                            "filename": os.path.basename(record.file.name),
                            "file": record.file.contents,
                            "findings": record.bound.parsed.findings_context,
                            "alert": record.alert,
                            "exception": record.exception,
                            "failed": record.failed,
                            "format": record.file.log_format,
                            "SiteLogFormat": SiteLogFormat,
                        },
                    )
                    log_file = self.logs / f"{record.index.site.name}.html"
                    if self.verbosity > 1:
                        self.secho(
                            _("Writing parsing log for {station} to {log_file}").format(
                                station=record.index.site.name, log_file=log_file
                            ),
                            fg="blue",
                        )
                    with open(log_file, "wt") as log_f:
                        log_f.write(file_log)
                    p_bar.update(n=1)

            # todo write index
            log_index = render_to_string(
                self.log_index_tmpl,
                {
                    "command": " ".join([Path(sys.argv[0]).name, *sys.argv[1:]]),
                    "runtime": datetime.now(),
                    "imports": self.imports,
                    "failed_imports": self.failed_imports,
                    "total_warnings": self.total_warnings,
                    "total_errors": self.total_errors,
                },
            )
            index_file = self.logs / "index.html"
            with open(index_file, "wt") as log_f:
                log_f.write(log_index)

            if self.verbosity > 0:
                return index_file.absolute()

    def update_head(self, record: ImportRecord) -> bool:
        index = record.index
        for fmt in self.formats:
            record.file = index.files.filter(log_format=fmt).first()
            if record.file:
                break

        if not record.file:
            record.failed = _(
                "Unable to find a current indexed file in one of the specified formats: {formats}"
            ).format(formats=self.formats)
            return False

        with transaction.atomic():
            # clear *all* current data for the site!
            for section in self.SECTION_MODELS.values():
                section.objects.filter(site=index.site).delete()
            ########################

            ImportAlert.objects.filter(site=index.site).delete()
            record.bound = record.file.parse()
            alert = {}
            for section in reversed(record.bound.parsed.sections.values()):
                if not section.contains_values:
                    # likely a placeholder section
                    continue

                section_model = self.SECTION_MODELS.get(section.heading_index, None)
                if (
                    not section_model
                    or not inspect.isclass(section_model)
                    or not issubclass(section_model, SiteSection)
                ):
                    finding_at_line = record.bound.parsed.findings.get(
                        section.line_no, None
                    )
                    if (
                        finding_at_line is None
                        or finding_at_line.priority < Warn.priority
                    ):
                        record.bound.parsed.add_finding(
                            Warn(
                                lineno=section.line_no,
                                parser=section.parser,
                                message=_("Unexpected section!"),
                                section=section,
                            )
                        )
                    continue

                field_updates = {
                    "site": index.site,
                    "published": True,
                    "edited": index.begin,
                    "_flags": {},
                }
                # many-many relations have to be set differently
                many_relations = {}
                try:
                    if not section.binding:
                        continue
                    for field, value in section.binding.items():
                        try:
                            if field := section_model._meta.get_field(field):
                                if isinstance(field, models.ManyToManyField):
                                    many_relations[field.name] = value
                                    continue
                                elif isinstance(
                                    field, models.fields.related.RelatedField
                                ):
                                    if not isinstance(value, field.related_model):
                                        value = field.related_model.objects.get_by_natural_key(
                                            value
                                        )
                                field_updates[field.name] = value
                        except FieldDoesNotExist:
                            pass
                except ObjectDoesNotExist:
                    alert["level"] = AlertLevel.ERROR
                    alert.setdefault("detail", "")
                    alert["detail"] = _(
                        "{detail}Unable to resolve '{value}'\n."
                    ).format(detail=alert["detail"], value=value)
                    continue

                for parameter in section.parameters.values():
                    # pull out the parser findings based on line number, and add them as admin flags
                    # todo binder/parser interface should make this easier
                    for var in (parameter.binding or {}).keys():
                        if var not in field_updates:
                            continue
                        error = None
                        warning = None
                        for line_no in range(parameter.line_no, parameter.line_end + 1):
                            if error := record.bound.parsed.errors.get(line_no, None):
                                break
                            if not warning:
                                warning = record.bound.parsed.warnings.get(
                                    line_no, None
                                )

                        flag = error or warning
                        if flag:
                            field_updates["_flags"][var] = (
                                f"Import issue?: {flag.message}"
                            )

                field_updates["num_flags"] = len(field_updates["_flags"])
                if isinstance(section_model, SiteSubSection):
                    field_updates["subsection"] = section.heading_index[-1]

                try:
                    if section_model is SiteForm:
                        form = SiteForm()
                        for field, value in field_updates.items():
                            setattr(form, field, value)
                        form.previous = (
                            ArchiveIndex.objects.filter(
                                site=index.site,
                                valid_range__startswith__lte=index.begin,
                            )
                            .order_by("-valid_range")
                            .first()
                        )
                        form.save(skip_update=True, set_previous=False)
                    else:
                        model = section_model.objects.create(**field_updates)
                        if many_relations:
                            for field, relations in many_relations.items():
                                getattr(model, field).set(relations)
                            model.save()
                except DatabaseError as db_err:
                    finding_at_line = record.bound.parsed.findings.get(
                        section.line_no, None
                    )
                    if (
                        finding_at_line is None
                        or finding_at_line.priority < Error.priority
                    ):
                        record.bound.parsed.add_finding(
                            Error(
                                lineno=section.line_no,
                                parser=section.parser,
                                message=_("Unable to save section: {}").format(
                                    str(db_err)
                                ),
                                section=section,
                            )
                        )
                    raise

            self.total_errors += len(record.bound.parsed.errors)
            self.total_warnings += len(record.bound.parsed.warnings)
            if record.bound.parsed.errors or record.bound.parsed.warnings:
                level = (
                    AlertLevel.ERROR
                    if record.bound.parsed.errors
                    else AlertLevel.WARNING
                )
                alert.setdefault("level", level)
                if alert["level"].value < level.value:
                    alert["level"] = level
                alert.update(
                    {
                        "file_contents": "\n".join(record.bound.lines),
                        "findings": record.bound.parsed.findings_context,
                        "log_format": record.file.log_format,
                    }
                )
            if alert:
                alert["site"] = index.site
                alert.setdefault("level", AlertLevel.WARNING)
                if alert["level"] is AlertLevel.ERROR:
                    alert.setdefault(
                        "header", _("Errors were encountered during import.")
                    )
                    self.errors += 1
                if alert["level"] is AlertLevel.WARNING:
                    alert.setdefault(
                        "header", _("Warnings were encountered during import.")
                    )
                    self.warnings += 1
                record.alert = ImportAlert.objects.create(**alert)

            if index.site.status in [
                *SiteLogStatus.active_states(),
                SiteLogStatus.EMPTY,
            ]:
                index.site.status = SiteLogStatus.PUBLISHED
                index.site.save()

            index.site.synchronize(skip_form_updates=True)
            return True
