import os
import typing as t
from datetime import datetime, timezone
from io import BytesIO
from logging import getLogger
from pathlib import Path

from dateutil import parser
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models as gis_models
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.timezone import is_naive, make_aware, now
from django.utils.translation import gettext as _
from django_enum import EnumField
from packaging.version import Version
from packaging.version import parse as parse_version
from PIL import Image
from polymorphic.managers import PolymorphicManager, PolymorphicQuerySet
from polymorphic.models import PolymorphicModel

from slm.defines import (
    CardinalDirection,
    GeodesyMLVersion,
    LogEntryType,
    SiteFileUploadStatus,
    SiteLogFormat,
    SLMFileType,
)
from slm.models.sitelog import DefaultToStrEncoder
from slm.singleton import SingletonModel
from slm.utils import get_exif_tags


def site_upload_path(instance: "SiteFile", filename: str) -> str:
    """
    file will be saved to:
        MEDIA_ROOT/uploads/<site name>/filename

    If there is a name collision with a file on disk, the _HHMMSS from the file's
    timestamp will be added onto the name. If the collision is with an ArchivedSiteLog
    the file already on disk will have its name changed to include the timestamp. This
    keeps the most recently indexed file for each day having just the date timestamp.

    :param filename: The name of the file
    :return: The path where the site file should reside.
    """
    from .index import ArchivedSiteLog

    prefix = Path()
    if instance.SUB_DIRECTORY:
        prefix = Path(instance.SUB_DIRECTORY)
    dest = prefix / instance.site.name / filename
    timestamp = (
        instance.index.begin
        if isinstance(instance, ArchivedSiteLog)
        else instance.timestamp
    )
    if (Path(settings.MEDIA_ROOT) / dest).exists():
        stem, suffix = dest.stem, dest.suffix
        if isinstance(instance, ArchivedSiteLog):
            # TODO - there is potential here for the database to be out of sync with the filesytem if the outer
            # transaction fails
            try:
                for archive in ArchivedSiteLog.objects.filter(
                    file__endswith=str(dest.as_posix())
                ):
                    current_path = Path(archive.file.path)
                    new_path = Path(archive.file.path)
                    if current_path.stem.count("_") < 2:
                        new_path = current_path.with_name(
                            f"{current_path.stem}_{archive.index.valid_range.lower.strftime('%H%M%S')}{current_path.suffix}"
                        )
                        archive.file.name = archive.file.name.replace(
                            current_path.name, new_path.name
                        )
                        archive.name = Path(archive.file.name).name
                        current_path.rename(new_path)
                        archive.save(update_fields=["file", "name"])
            except ArchivedSiteLog.DoesNotExist:
                (Path(settings.MEDIA_ROOT) / dest).unlink()
        else:
            dest = dest.with_name(f"{stem}_{timestamp.strftime('%H%M%S')}{suffix}")
    return dest.as_posix()


def site_thumbnail_path(instance: "SiteFile", filename: str) -> str:
    """
    Return the path for the thumbnail image for the given filename.

    :param filename: The name of the file
    :return: The path where the thumbnail image should reside.
    """
    path = Path(instance.upload_path(filename))
    return (path.parent / "thumbnails" / path.name).as_posix()


class AgencyManager(models.Manager):
    pass


class AgencyQuerySet(models.QuerySet):
    def membership(self, user):
        """Get the agency(s) this user is a member of."""
        if user.is_authenticated:
            if user.is_superuser:
                return self
            return user.agencies.all()
        return self.none()

    def public(self):
        """
        Public agencies show up in all unauthenticated interfaces and APIs.
        The must be both active and public.
        :return:
        """
        return self.filter(active=True, public=True)

    def visible_to(self, user):
        """
        If authenticated and superuser return everything. If not authenticated
        return only public stations, if not super user and authenticated return
        all public agencies and any non-public agencies the user is a member
        of.

        :param user: The user object associated with the request.
        :return:
        """
        if user.is_authenticated and user.is_superuser:
            return self
        return self.public() | self.membership(user)


class Agency(models.Model):
    id = models.AutoField(primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=100, blank=False, null=False, db_index=True)
    shortname = models.CharField(max_length=20, blank=False, null=False, db_index=True)

    url = models.URLField(max_length=255, blank=True, null=True)

    address = models.CharField(max_length=50, blank=True, null=True)
    address2 = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=30, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    phone1 = models.CharField(max_length=20, blank=True, null=True)
    phone2 = models.CharField(max_length=20, blank=True, null=True)
    email1 = models.EmailField(max_length=100, blank=True, null=True)
    email2 = models.EmailField(max_length=100, blank=True, null=True)
    contact = models.CharField(max_length=50, blank=True, null=True)
    other = models.TextField(blank=True, null=True)
    active = models.BooleanField(blank=True, null=False, default=True)
    created = models.DateTimeField(blank=True, auto_now_add=True)

    public = models.BooleanField(
        blank=True,
        default=True,
        null=False,
        help_text=_(
            "Set to false to exclude all sites affiliated with this agency "
            "from public exposure."
        ),
        db_index=True,
    )

    objects = AgencyManager.from_queryset(AgencyQuerySet)()

    def __str__(self):
        return self.name

    class Meta:
        managed = True


class NetworkManager(models.Manager):
    pass


class NetworkQuerySet(models.QuerySet):
    def public(self):
        return self.filter(public=True)

    def visible_to(self, user):
        if user.is_authenticated and user.is_superuser:
            return self
        return self.public()


class Network(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False, db_index=True)

    public = models.BooleanField(
        null=False,
        default=True,
        blank=True,
        db_index=True,
        help_text=_(
            "If false, this network will not appear in publicly facing data,"
            "interfaces and APIs."
        ),
    )

    sites = models.ManyToManyField("slm.Site", related_name="networks")

    objects = NetworkManager.from_queryset(NetworkQuerySet)()

    def __str__(self):
        return self.name


class SiteFile(models.Model):
    SUB_DIRECTORY = "misc"

    logger = getLogger("slm.models.system.SiteFile")

    site = models.ForeignKey(
        "slm.Site",
        on_delete=models.CASCADE,
        null=False,
        help_text=_("The site this file is attached to."),
        related_name="%(class)ss",
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When the file was created or uploaded."),
    )

    file = models.FileField(
        upload_to=site_upload_path,
        null=False,
        max_length=255,
        help_text=_("A pointer to the uploaded file on disk."),
        unique=True,
    )

    size = models.PositiveIntegerField(
        null=True, default=None, blank=True, db_index=True
    )

    thumbnail = models.ImageField(
        upload_to=site_thumbnail_path,
        null=True,
        default=None,
        blank=True,
        help_text=_("A pointer to the generated thumbnail file on disk."),
    )

    mimetype = models.CharField(
        max_length=255,
        null=False,
        default="",
        db_index=True,
        help_text=_("The mimetype of the file."),
    )

    file_type = EnumField(
        SLMFileType,
        null=False,
        default=SLMFileType.ATTACHMENT,
        db_index=True,
        help_text=_("The file type of the upload."),
    )

    log_format = EnumField(
        SiteLogFormat,
        null=True,
        default=None,
        db_index=True,
        help_text=_("The site log format. (Only if file_type is Site Log)"),
    )

    gml_version = EnumField(
        GeodesyMLVersion,
        null=True,
        default=None,
        db_index=True,
        help_text=_("The Geodesy ML version. (Only if file_type is GeodesyML)"),
    )

    @property
    def on_disk(self) -> Path:
        return Path(self.file.path)

    def update_directory(self):
        for file in [self.file, self.thumbnail]:
            if not file or not file.path:
                continue

            old_file_path = file.path
            new_name = file.field.upload_to(self, os.path.basename(file.name))
            new_file_path = file.storage.path(new_name)

            if old_file_path != new_file_path:
                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                file.name = new_name
                os.rename(old_file_path, new_file_path)
                self.save()
                old_dir = os.path.dirname(old_file_path)
                if not os.listdir(old_dir):
                    os.rmdir(old_dir)

    def rotate(self, degrees_ccw=90):
        if self.file and self.file_type is SLMFileType.SITE_IMAGE:
            from PIL import Image

            img = Image.open(self.file.path)
            out = img.rotate(int(degrees_ccw), expand=True)
            out.save(self.file.path)
            self.generate_thumbnail(regenerate=True)

    def save(self, *args, **kwargs):
        self._discover_type()
        if self.pk is None:
            self._exif_transpose()
        self.generate_thumbnail()
        if self.file:
            self.size = self.file.size
        else:
            self.size = None
        return super().save(*args, **kwargs)

    def _discover_type(self):
        if not self.mimetype or self.mimetype == "application/octet-stream":
            import mimetypes

            self.mimetype = mimetypes.guess_type(self.file.path)[0]
            if not self.mimetype:
                self.mimetype = "application/octet-stream"
        if self.file_type in [SLMFileType.ATTACHMENT, None]:
            self.file_type, self.log_format = self.determine_type(
                self.file, self.mimetype
            )

    @classmethod
    def determine_type(cls, file, mimetype):
        file_type, log_format = SLMFileType.ATTACHMENT, None
        if mimetype == SiteLogFormat.LEGACY.mimetype:
            # todo - better criteria??
            upl = file.open()
            content = upl.read()
            if (
                b"Site Identification of the GNSS Monument" in content
                and b"Site Location Information" in content
                and b"GNSS Receiver Information" in content
                and b"GNSS Antenna Information" in content
            ):
                if b"Nine Character ID" in content:
                    return SLMFileType.SITE_LOG, SiteLogFormat.ASCII_9CHAR
                return SLMFileType.SITE_LOG, SiteLogFormat.LEGACY
        elif mimetype == SiteLogFormat.GEODESY_ML.mimetype:
            # todo - determine if this is the right schema etc, otherwise
            # could be an XML file attachment
            return SLMFileType.SITE_LOG, SiteLogFormat.GEODESY_ML
        elif mimetype == SiteLogFormat.JSON.mimetype:
            pass
        elif mimetype and mimetype.split("/")[0] == "image" and "svg" not in mimetype:
            return SLMFileType.SITE_IMAGE, None

        return file_type, log_format

    def _exif_transpose(self):
        """
        Transpose the image to match the EXIF orientation if it exists and
        is other than 1.
        :return:
        """
        if self.file_type is SLMFileType.SITE_IMAGE and self.file:
            from PIL import ImageOps

            buffer = BytesIO()
            ImageOps.exif_transpose(Image.open(self.file.open("rb"))).save(
                buffer, format=self.mimetype.split("/")[1].upper()
            )
            buffer.seek(0)
            self.file.save(
                self.file.name,
                ContentFile(buffer.read()),
                save=False,
            )

    def generate_thumbnail(self, regenerate=False):
        """
        Generate a thumbnail image for this file if it is an image.

        :param regenerate: If true, delete and regenerate the existing image.
        :return:
        """
        if (
            self.file_type is SLMFileType.SITE_IMAGE
            and (regenerate or not self.has_thumbnail)
            and self.file.path
        ):
            try:
                image = Image.open(self.file.open("rb")).copy().convert("RGB")
                max_dim = getattr(settings, "SLM_THUMBNAIL_SIZE", 250)
                image.thumbnail(
                    (
                        (image.width * (max_dim / image.height), max_dim)
                        if image.height > image.width
                        else (max_dim, image.height * (max_dim / image.width))
                    ),
                    Image.LANCZOS,
                )
                buffer = BytesIO()
                image.save(buffer, "JPEG")
                buffer.seek(0)
                if self.has_thumbnail:
                    try:
                        os.remove(self.thumbnail.path)
                    except OSError:
                        pass
                self.thumbnail.save(
                    getattr(
                        self,
                        "name",
                        ".".join(
                            [*os.path.basename(self.file.path).split(".")[0:-1], "jpeg"]
                        ),
                    ),
                    ContentFile(buffer.read()),
                    save=False,
                )
                buffer.close()
            except Exception:
                self.logger.exception("Error creating thumbnail for %s", self)

    @property
    def has_thumbnail(self):
        return (
            self.thumbnail
            and self.thumbnail.path
            and os.path.exists(self.thumbnail.path)
        )

    def __str__(self):
        if hasattr(self, "name"):
            return f"[{self.site.name}] {self.name}"
        return f"[{self.site.name}] {os.path.basename(self.file.path)}"

    class Meta:
        abstract = True
        ordering = ("-timestamp",)


class SiteFileUploadManager(models.Manager):
    pass


class SiteFileUploadQuerySet(models.QuerySet):
    @staticmethod
    def public_q(public_sites_only=True):
        """
        Return a Q object holding the public definition. Which is any file
        that belongs to a public site that is in the PUBLISHED state.

        :return: Q object holding the definition of "public"
        """
        from slm.models.sitelog import Site

        return (
            Q(status=SiteFileUploadStatus.PUBLISHED) & Q(site__in=Site.objects.public())
            if public_sites_only
            else Q()
        )

    def public(self, public_sites_only=True):
        """
        Fetch the files that are public. This is any file that belongs to a
        public site that is in the PUBLISHED state.

        :return: A queryset containing the public files
        """
        return self.filter(self.public_q(public_sites_only))

    def available_to(self, user):
        """
        Fetch the files that are available to the given user. This is any
        public file or any file that is attached to a site a user has edit
        permissions to.

        :param user: The user (may be unauthenticated)
        :return: A queryset containing available files
        """
        from slm.models.sitelog import Site

        if not user.is_authenticated:
            return self.public()
        return self.filter(
            self.public_q(public_sites_only=False)
            | (Q(site__in=Site.objects.editable_by(user)))
        )


class SiteFileUpload(SiteFile):
    """
    SiteFileUploads can be any file that was uploaded to a given site.
    This includes, images and attachments as well as legacy site logs,
    GeodesyML files or json files. Access to the files for download publicly
    and by authenticated users is controlled in the manager/queryset above.

    Only images and attachments are made available for download publicly.
    Uploaded log files are ephemeral - for downloads of rendered log files
    from disk see ArchivedSiteLog.
    """

    SUB_DIRECTORY = "uploads"

    name = models.CharField(
        blank=False, db_index=True, max_length=255, help_text=_("The name of the file.")
    )

    created = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text=_("The date and time the file was created."),
    )

    status = EnumField(
        SiteFileUploadStatus,
        default=SiteFileUploadStatus.UNPUBLISHED,
        null=False,
        blank=True,
        db_index=True,
        help_text=_(
            "The status of the file. This will also depend on what type the file is."
        ),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_("The user that uploaded the file."),
    )

    # context generated at the time of upload - will be added to upload page
    # rendering for the file.
    context = models.JSONField(
        null=False, blank=True, default=dict, encoder=DefaultToStrEncoder
    )

    description = models.TextField(
        blank=True,
        default="",
        help_text=_("A description of what this file is (optional)."),
    )

    direction = EnumField(
        CardinalDirection,
        blank=True,
        default=None,
        null=True,
        help_text=_(
            "For images taken at the site, this is the cardinal direction the "
            "camera was pointing towards."
        ),
    )

    objects = SiteFileUploadManager.from_queryset(SiteFileUploadQuerySet)()

    def save(self, *args, **kwargs):
        self._discover_type()
        # if this is an image, attempt to pull the real timestamp out of the
        # meta data
        if not self.created and self.file_type == SLMFileType.SITE_IMAGE:
            tags = get_exif_tags(self.file.open("rb"))
            for tag in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
                if tag in tags:
                    try:
                        self.created = datetime.strptime(tags[tag], "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        try:
                            self.created = parser.parse(tags[tag])
                        except parser.ParserError:
                            pass

                    if self.created:
                        if is_naive(self.created):
                            self.created = make_aware(self.created, timezone.utc)
                        break
        return super().save(*args, **kwargs)

    @property
    def link(self):
        return reverse("slm_public_api:files-detail", kwargs={"pk": self.pk})

    @property
    def edit_link(self):
        return (
            reverse(
                "slm_edit_api:files-detail",
                kwargs={"pk": self.pk, "site": self.site.name},
            )
            + "?download"
        )

    @property
    def thumbnail_link(self):
        lnk = reverse("slm_public_api:files-detail", kwargs={"pk": self.pk})
        return f"{lnk}?thumbnail=1"

    @property
    def edit_thumbnail_link(self):
        lnk = reverse(
            "slm_edit_api:files-detail", kwargs={"pk": self.pk, "site": self.site.name}
        )
        return f"{lnk}?thumbnail=1&download"

    class Meta:
        ordering = ("-timestamp",)
        verbose_name_plural = "Site File Uploads"


class LogEntryManager(PolymorphicManager):
    pass


class LogEntryQuerySet(PolymorphicQuerySet):
    def for_user(self, user):
        if user.is_superuser:
            return self
        return self.filter(site__agencies__in=user.agencies.all())


class LogEntry(PolymorphicModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        related_name="logentries",
    )

    timestamp = models.DateTimeField(null=False, blank=True, db_index=True)

    type = EnumField(LogEntryType, null=False, blank=False, db_index=True)

    site = models.ForeignKey(
        "slm.Site",
        on_delete=models.CASCADE,
        null=True,
        default=None,
        blank=True,
        related_name="edit_history",
    )

    section = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        default=None,
        blank=True,
        related_name="edit_history",
    )

    subsection = models.PositiveSmallIntegerField(null=True, default=None, blank=True)

    file = models.ForeignKey(
        "slm.SiteFileUpload", null=True, default=None, on_delete=models.SET_NULL
    )

    ip = models.GenericIPAddressField(null=True, default=None, blank=True)

    objects = LogEntryManager.from_queryset(LogEntryQuerySet)()

    def save(self, *args, **kwargs):
        if not self.timestamp:
            self.timestamp = now()
        return super().save(*args, **kwargs)

    @property
    def link(self):
        """Return a link to the most relevant view for the log entry."""
        if hasattr(self, "section") and self.section:
            section_link = reverse(
                "slm:edit",
                kwargs={
                    "station": self.site.name,
                    "section": self.section.model_class().section_slug(),
                },
            )
            if self.subsection is not None and self.type != LogEntryType.DELETE:
                section_link += f"#{self.subsection}"
            return section_link
        elif hasattr(self, "file") and self.file:
            return reverse(
                "slm:upload", kwargs={"station": self.site.name, "file": self.file.id}
            )
        elif self.type in {LogEntryType.ATTACHMENT_DELETE, LogEntryType.IMAGE_DELETE}:
            return reverse("slm:upload", kwargs={"station": self.site.name})
        elif hasattr(self, "site") and self.site:
            return reverse("slm:review", kwargs={"station": self.site.name})
        return None

    def __str__(self):
        return (
            f"({self.site.name} | "
            f"{self.user.name or self.user.email if self.user else ''}) "
            f"[{self.timestamp}]: {self.type} -> "
            f"{self.section or self.file or self.site or ''}"
        )

    class Meta:
        ordering = ("-timestamp",)
        verbose_name_plural = "Log Entries"
        verbose_name = "Log Entry"
        unique_together = (("timestamp", "type", "site", "section", "subsection"),)
        indexes = [
            models.Index(fields=("timestamp", "type", "site", "section", "subsection"))
        ]


class TideGauge(gis_models.Model):
    name = models.CharField(max_length=128, blank=True, null=False, db_index=True)

    position = gis_models.PointField(null=True, blank=True, srid=4326, geography=True)

    sonel_id = models.IntegerField(blank=True, null=True, db_index=True)

    sites = models.ManyToManyField(
        "slm.Site",
        through="slm.SiteTideGauge",
        through_fields=("gauge", "site"),
        related_name="tide_gauges",
    )

    @property
    def sonel_link(self):
        if self.sonel_id:
            return (
                f"http://www.sonel.org/spip.php?page=maregraphe"
                f"&idStation={self.sonel_id}"
            )
        return ""

    @property
    def link(self):
        return self.sonel_link  # or ...

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tide Gauge"
        verbose_name_plural = "Tide Gauges"
        ordering = ("name",)


class SiteTideGauge(models.Model):
    site = models.ForeignKey(
        "slm.Site", on_delete=models.CASCADE, related_name="tide_gauge_distances"
    )
    gauge = models.ForeignKey(
        TideGauge, on_delete=models.CASCADE, related_name="site_distances"
    )

    distance = models.IntegerField(blank=True, null=False, db_index=True)

    def __str__(self):
        return f"{self.site.name} {self.gauge.name}"

    class Meta:
        ordering = ("site", "distance")


class SLMVersion(SingletonModel):
    """
    We store the SLM code version in the database to enable safe upgrades.
    """

    version_str = models.CharField(default="", blank=True)

    @classmethod
    def update(cls, version: t.Optional[t.Union[Version, str]] = None):
        if not version:
            from slm import __version__ as slm_version

            version = slm_version

        if isinstance(version, str):
            version = parse_version(version)

        instance = cls.load()
        instance.version_str = str(version)  # normalized!
        instance.save()

    @property
    def version(self) -> t.Optional[Version]:
        if self.version_str:
            return parse_version(self.version_str)
        return None
