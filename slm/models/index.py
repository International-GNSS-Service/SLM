import os

from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import F, OuterRef, Q, Subquery, Value
from django.db.models.functions import (
    Cast,
    Concat,
    ExtractDay,
    ExtractMonth,
    ExtractYear,
    Lower,
    LPad,
    Now,
    Substr,
)
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from slm.defines import (
    GeodesyMLVersion,
    RinexVersion,
    SiteLogFormat,
    SiteLogStatus,
    SLMFileType,
)
from slm.models.data import DataAvailability
from slm.models.system import SiteFile
from slm.parsing import BaseBinder
from slm.parsing import legacy as legacy_parsing
from slm.parsing import xsd as xsd_parsing


class ArchiveIndexManager(models.Manager):
    def regenerate(self, site, log_format):
        """
        Regenerate the index file for this index. This will only be done for
        the head index for this file.

        :param site: The site to regenerate the archived index file for.
        :param log_format: The log format to regenerate.
        """
        new_file = ArchivedSiteLog.objects.from_index(
            index=self.get_queryset().filter(site=site).order_by("-begin").first(),
            log_format=log_format,
            regenerate=True,
        )
        return new_file

    def add_index(self, site, formats=list(SiteLogFormat)):
        assert site.last_publish, "last_publish must be set before calling add_index"
        existing = self.filter(site=site, begin=site.last_publish).first()
        if existing:
            return existing

        self.close_index(site)

        new_index = self.create(site=site, begin=site.last_publish, end=None)

        for log_format in formats:
            if log_format in {SiteLogFormat.JSON}:
                continue  # todo - remove
            ArchivedSiteLog.objects.from_site(site=site, log_format=log_format)

        return new_index

    def close_index(self, site):
        if site.last_publish:
            last = (
                self.filter(site=site)
                .filter(
                    Q(begin__lte=site.last_publish) & Q(end__isnull=True)
                    | Q(end__gt=site.last_publish)
                )
                .first()
            )
            if last:
                last.end = site.last_publish
                last.save()

    def create(self, **kwargs):
        return self.insert_index(**kwargs)

    def get_or_create(self, site, begin, **kwargs):
        self.insert_index(site=site, begin=begin, **kwargs)

    def insert_index(self, begin, site, **kwargs):
        """
        Insert a new index into an existing index deck (i.e. between existing
        indexes).
        """
        existing = self.get_queryset().filter(site=site, begin=begin).first()
        if existing:
            return existing
        next_index = (
            self.get_queryset()
            .filter(site=site, begin__gt=begin)
            .order_by("begin")
            .first()
        )
        prev_index = (
            self.get_queryset()
            .filter(site=site, begin__lt=begin)
            .order_by("-begin")
            .first()
        )
        kwargs.setdefault("end", next_index.begin if next_index else None)
        if prev_index:
            prev_index.end = begin
            prev_index.save()
        return super().create(begin=begin, site=site, **kwargs)


class ArchiveIndexQuerySet(models.QuerySet):
    def delete(self):
        """
        We can't just delete an archive to remove it - we also have to
        update the end time of the previous archive in the index if there
        is one to reflect the end time of the deleted log
        """
        from slm.models import Site, SiteForm

        with transaction.atomic():
            # also, sites where the deleted index is the current index
            # (end=null) that are in the published state should be set to
            # updated
            # we trigger unpublished state by updating the SiteForm
            # prepared date and synchronizing
            published_sites = Site.objects.filter(
                Q(indexes__in=self.filter(end__isnull=True))
                & Q(status=SiteLogStatus.PUBLISHED)
            ).distinct()

            # these are the indexes that remain that must be updated - that
            # includes any non-deleted index immediately preceding a deleted
            # index, indexes immediately following a deleted index do not
            # need to be updated
            after = self.filter(Q(site=OuterRef("site")) & Q(begin=OuterRef("end")))
            before = self.filter(Q(site=OuterRef("site")) & Q(end=OuterRef("begin")))
            new_bookends = (
                ArchiveIndex.objects.annotate(before=Subquery(before.values("pk")[:1]))
                .filter(
                    Q(site=OuterRef("site"))
                    & Q(begin__gte=OuterRef("end"))
                    & ~Q(pk__in=self)
                    & Q(before__isnull=False)
                )
                .order_by("end")
            )
            adjacent_indexes = ArchiveIndex.objects.annotate(
                adjacent=Subquery(after.values("pk")[:1]),
                new_end=Subquery(new_bookends.values("begin")[:1]),
            ).filter(Q(adjacent__isnull=False) & ~Q(pk__in=self))

            # we use the new last indexes' old last end date
            forms = []
            for form in SiteForm.objects.filter(site__in=published_sites):
                form.pk = None
                form.published = False
                form.date_prepared = now().date()
                forms.append(form)

            SiteForm.objects.bulk_create(forms)
            published_sites.synchronize_denormalized_state()

            adjacent_indexes.update(end=F("new_end"))
            deleted = super().delete()
            return deleted

    @staticmethod
    def epoch_q(epoch=None):
        if epoch is None:
            epoch = now()
        return Q(begin__lte=epoch) & (Q(end__gt=epoch) | Q(end__isnull=True))

    def at_epoch(self, epoch=None):
        return self.filter(self.epoch_q(epoch))

    def public(self):
        return self.filter(site__agencies__public=True)

    def availability(self):
        last_data_avail = DataAvailability.objects.filter(site=OuterRef("pk")).order_by(
            "-last"
        )
        return self.annotate(
            last_data_time=Subquery(last_data_avail.values("last")[:1]),
            last_data=Now() - F("last_data_time"),
            last_rinex2=Subquery(
                last_data_avail.filter(RinexVersion(2).major_q()).values("last")[:1]
            ),
            last_rinex3=Subquery(
                last_data_avail.filter(RinexVersion(3).major_q()).values("last")[:1]
            ),
            last_rinex4=Subquery(
                last_data_avail.filter(RinexVersion(4).major_q()).values("last")[:1]
            ),
        )

    def annotate_filenames(
        self, name_len=None, field_name="filename", lower_case=False, log_format=None
    ):
        """
        Add the log names (w/o) extension as a property called filename to
        each site.

        :param name_len: If given a number, the filename will start with only
            the first name_len characters of the site name.
        :param field_name: Change the name of the annotated field.
        :param lower_case: Filenames will be lowercase if true.
        :param log_format: If given, add the extension for the given format
        :return: A queryset with the filename annotation added.
        """
        name_str = F("site__name")
        if name_len:
            name_str = Cast(
                Substr("site__name", 1, length=name_len), models.CharField()
            )

        if lower_case:
            name_str = Lower(name_str)

        parts = [
            name_str,
            Value("_"),
            Cast(ExtractYear("begin"), models.CharField()),
            LPad(
                Cast(ExtractMonth("begin"), models.CharField()), 2, fill_text=Value("0")
            ),
            LPad(
                Cast(ExtractDay("begin"), models.CharField()), 2, fill_text=Value("0")
            ),
        ]
        if log_format:
            parts.append(Value(f".{log_format.ext}"))

        return self.annotate(**{field_name: Concat(*parts)})


class ArchiveIndex(models.Model):
    site = models.ForeignKey(
        "slm.Site", on_delete=models.CASCADE, null=False, related_name="indexes"
    )

    # the point in time at which this record begins being valid
    begin = models.DateTimeField(
        null=False,
        db_index=True,
        help_text=_("The point in time at which this archive became valid."),
    )

    # the point in time at which this record stops being valid
    end = models.DateTimeField(
        null=True,
        db_index=True,
        help_text=_("The point in time at which this archive stopped being valid."),
    )

    objects = ArchiveIndexManager.from_queryset(ArchiveIndexQuerySet)()

    def __str__(self):
        return (
            f"{self.site.name} | {self.begin.date()} - "
            f'{self.end.date() if self.end else "present"}'
        )

    def delete(self, using=None, keep_parents=False):
        """
        Deleting an index requires updating the end time of the previous
        indexes - we use the queryset delete method to do this.
        """
        return ArchiveIndex.objects.filter(pk=self.pk).delete()

    class Meta:
        ordering = ("-begin",)
        indexes = [
            models.Index(fields=("begin", "end")),
            models.Index(fields=("site", "begin", "end")),
        ]
        unique_together = (("site", "begin"),)
        verbose_name = "Archive Index"
        verbose_name_plural = "Archive Index"


class ArchivedSiteLogManager(models.Manager):
    """
    This manager is responsible for mediating access to serialized site logs.
    Most frequently it will be fetching logs that match the given criteria from
    disk, but it might also generate a log from the edit stack if an archived
    file does not exist.
    """

    def from_index(self, index, log_format, regenerate=False):
        from slm.api.serializers import SiteLogSerializer

        if index:
            file = index.files.filter(log_format=log_format).first()
            if file and not regenerate:
                return file
            elif file:
                file.delete()
            return self.model.objects.create(
                site=index.site,
                log_format=log_format,
                index=index,
                timestamp=index.begin,
                mimetype=log_format.mimetype,
                file_type=SLMFileType.SITE_LOG,
                name=index.site.get_filename(log_format=log_format, epoch=index.begin),
                file=ContentFile(
                    SiteLogSerializer(instance=index.site)
                    .format(log_format)
                    .encode("utf-8"),
                    name=index.site.get_filename(
                        log_format=log_format, epoch=index.begin
                    ),
                ),
                gml_version=(
                    GeodesyMLVersion.latest()
                    if log_format is SiteLogFormat.GEODESY_ML
                    else None
                ),
            )
        return None

    def from_site(self, site, log_format=SiteLogFormat.LEGACY, epoch=None):
        index = ArchiveIndex.objects.filter(site=site).at_epoch(epoch=epoch).first()
        if index:
            return self.from_index(index, log_format=log_format)
        return None


class ArchivedSiteLogQuerySet(models.QuerySet):
    def annotate_filenames(
        self, name_len=None, field_name="filename", lower_case=False, log_format=None
    ):
        """
        Add the log names (w/o) extension as a property called filename to
        each site.

        :param name_len: If given a number, the filename will start with only
            the first name_len characters of the site name.
        :param field_name: Change the name of the annotated field.
        :param lower_case: Filenames will be lowercase if true.
        :param log_format: If given, add the extension for the given format
        :return: A queryset with the filename annotation added.
        """
        name_str = F("site__name")
        if name_len:
            name_str = Cast(
                Substr("site__name", 1, length=name_len), models.CharField()
            )

        if lower_case:
            name_str = Lower(name_str)

        parts = [
            name_str,
            Value("_"),
            Cast(ExtractYear("index__begin"), models.CharField()),
            LPad(
                Cast(ExtractMonth("index__begin"), models.CharField()),
                2,
                fill_text=Value("0"),
            ),
            LPad(
                Cast(ExtractDay("index__begin"), models.CharField()),
                2,
                fill_text=Value("0"),
            ),
        ]
        if log_format:
            parts.append(Value(f".{log_format.ext}"))
        return self.annotate(**{field_name: Concat(*parts)})


class ArchivedSiteLog(SiteFile):
    SUB_DIRECTORY = "archive"

    index = models.ForeignKey(
        ArchiveIndex, on_delete=models.CASCADE, related_name="files"
    )

    name = models.CharField(max_length=50)

    objects = ArchivedSiteLogManager.from_queryset(ArchivedSiteLogQuerySet)()

    def __str__(self):
        if self.name:
            return f"[{self.index}] {self.name}"
        return f"[{self.index}] {os.path.basename(self.file.path)}"

    def parse(self) -> BaseBinder:
        if self.log_format is SiteLogFormat.GEODESY_ML:
            return xsd_parsing.SiteLogBinder(
                xsd_parsing.SiteLogParser(self.contents, site_name=self.site.name)
            )
        elif self.log_format in [SiteLogFormat.LEGACY, SiteLogFormat.ASCII_9CHAR]:
            return legacy_parsing.SiteLogBinder(
                legacy_parsing.SiteLogParser(self.contents, site_name=self.site.name)
            )
        raise NotImplementedError(
            _("{format} is not currently supported for site log parsing.").format(
                format=self.log_format
            )
        )

    @cached_property
    def contents(self) -> str:
        """
        Decode the contents of a log file. The site log format has been around since the
        early 1990s so we may encounter exotic encodings.

        :param contents: The bytes of the log file contents.
        :return a decoded string of the contents
        """
        file_bytes = self.file.open("rb").read()
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return file_bytes.decode("ascii")
            except UnicodeDecodeError:
                return file_bytes.decode("latin")

    class Meta:
        unique_together = ("index", "log_format")
