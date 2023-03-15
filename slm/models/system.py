import os
from io import BytesIO
from logging import getLogger

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django_enum import EnumField
from PIL import Image
from slm.defines import (
    CardinalDirection,
    LogEntryType,
    SiteFileUploadStatus,
    SiteLogFormat,
    SLMFileType
)
from polymorphic.models import PolymorphicModel
from polymorphic.managers import PolymorphicManager, PolymorphicQuerySet
from slm.models import compat
from slm.models.sitelog import DefaultToStrEncoder, SiteSection, SiteSubSection
from slm.utils import get_exif_tags
from dateutil import parser
from datetime import datetime
from django.utils.timezone import is_naive, make_aware, utc


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
    name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True
    )
    shortname = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True
    )

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
            'Set to false to exclude all sites affiliated with this agency '
            'from public exposure.'
        ),
        db_index=True
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

    name = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        db_index=True
    )

    public = models.BooleanField(
        null=False,
        default=True,
        blank=True,
        db_index=True,
        help_text=_(
            'If false, this network will not appear in publicly facing data,'
            'interfaces and APIs.'
        )
    )

    sites = models.ManyToManyField('slm.Site', related_name='networks')

    objects = NetworkManager.from_queryset(NetworkQuerySet)()

    def __str__(self):
        return self.name


def site_upload_path(instance, filename):
    """
     file will be saved to:
        MEDIA_ROOT/uploads/<9-char site name>/filename

    :param instance: The SiteFile instance
    :param filename: The name of the file
    :return: The path where the site file should reside.
    """
    prefix = ''
    if instance.SUB_DIRECTORY:
        prefix = f'{instance.SUB_DIRECTORY}/'
    return f'{prefix}{instance.site.name}/{filename}'


def site_thumbnail_path(instance, filename):
    """
    Return the path for the thumbnail image for the given filename.

    :param instance: The SiteFile instance
    :param filename: The name of the file
    :return: The path where the thumbnail image should reside.
    """
    parts = str(site_upload_path(instance, filename)).split('/')
    return '/'.join([*parts[0:-1], 'thumbnails', parts[-1]])


class SiteFile(models.Model):

    SUB_DIRECTORY = 'misc'

    logger = getLogger('slm.models.system.SiteFile')

    site = models.ForeignKey(
        'slm.Site',
        on_delete=models.CASCADE,
        null=False,
        help_text=_('The site this file is attached to.'),
        related_name="%(class)ss"
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_('When the file was uploaded.')
    )

    file = models.FileField(
        upload_to=site_upload_path,
        null=False,
        max_length=255,
        help_text=_('A pointer to the uploaded file on disk.')
    )

    size = models.PositiveIntegerField(null=True, default=None, blank=True)

    thumbnail = models.ImageField(
        upload_to=site_thumbnail_path,
        null=True,
        default=None,
        blank=True,
        help_text=_('A pointer to the generated thumbnail file on disk.')
    )

    mimetype = models.CharField(
        max_length=255,
        null=False,
        default='',
        db_index=True,
        help_text=_('The mimetype of the file.')
    )

    file_type = EnumField(
        SLMFileType,
        null=False,
        default=SLMFileType.ATTACHMENT,
        db_index=True,
        help_text=_('The file type of the upload.')
    )

    log_format = EnumField(
        SiteLogFormat,
        null=True,
        default=None,
        db_index=True,
        help_text=_('The site log format. (Only if file_type is Site Log)')
    )

    def save(self, *args, **kwargs):
        self._discover_type()
        self.generate_thumbnail()
        if self.file:
            self.size = self.file.size
        else:
            self.size = None
        return super().save(*args, **kwargs)

    def _discover_type(self):
        if not self.mimetype:
            import mimetypes
            self.mimetype = mimetypes.guess_type(self.file.path)[0]
        if self.file_type in [SLMFileType.ATTACHMENT, None]:
            self.file_type, self.log_format = self.determine_type(
                self.file,
                self.mimetype
            )

    @classmethod
    def determine_type(cls, file, mimetype):
        file_type, log_format = SLMFileType.ATTACHMENT, None
        if mimetype == SiteLogFormat.LEGACY.mimetype:
            # todo - better criteria??
            upl = file.open()
            content = upl.read().decode()
            if (
                'Site Identification of the GNSS Monument' in content and
                'Site Location Information' in content and
                'GNSS Receiver Information' in content and
                'GNSS Antenna Information' in content
            ):
                return SLMFileType.SITE_LOG, SiteLogFormat.LEGACY
        elif mimetype == SiteLogFormat.GEODESY_ML.mimetype:
            # todo - determine if this is the right schema etc, otherwise
            # could be an XML file attachment
            return SLMFileType.SITE_LOG, SiteLogFormat.GEODESY_ML
        elif mimetype == SiteLogFormat.JSON.mimetype:
            pass
        elif mimetype.split('/')[0] == 'image' and 'svg' not in mimetype:
            return SLMFileType.SITE_IMAGE, None

        return file_type, log_format

    def generate_thumbnail(self, regenerate=False):
        """
        Generate a thumbnail image for this file if it is an image.

        :param regenerate: If true, delete and regenerate the existing image.
        :return:
        """
        if (
            self.file_type == SLMFileType.SITE_IMAGE and
            (regenerate or not self.has_thumbnail) and self.file.path
        ):
            try:
                image = Image.open(self.file.open('rb')).copy().convert('RGB')
                image.thumbnail(
                    getattr(settings, 'SLM_THUMBNAIL_SIZE', (250, 250)),
                    Image.ANTIALIAS
                )
                buffer = BytesIO()
                image.save(buffer, 'JPEG')
                buffer.seek(0)
                if self.has_thumbnail:
                    try:
                        os.remove(self.thumbnail.path)
                    except OSError:
                        pass
                self.thumbnail.save(
                    getattr(
                        self,
                        'name',
                        '.'.join([
                            *os.path.basename(self.file.path).split('.')[0:-1],
                            'jpeg']
                        )
                    ),
                    ContentFile(buffer.read()),
                    save=False,
                )
                buffer.close()
            except Exception:
                self.logger.exception('Error creating thumbnail for %s', self)

    @property
    def has_thumbnail(self):
        return (
            self.thumbnail and
            self.thumbnail.path and
            os.path.exists(self.thumbnail.path)
        )

    def __str__(self):
        if hasattr(self, 'name'):
            return f'[{self.site.name}] {self.name}'
        return f'[{self.site.name}] {os.path.basename(self.file.path)}'

    class Meta:
        abstract = True
        ordering = ('-timestamp',)


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
                Q(status=SiteFileUploadStatus.PUBLISHED) &
                Q(site__in=Site.objects.public()) if public_sites_only else Q()
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
        return self.filter(self.public_q(public_sites_only=False) | (
            Q(site__in=Site.objects.editable_by(user))
        ))


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

    SUB_DIRECTORY = 'uploads'

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=255,
        help_text=_('The name of the file.')
    )

    created = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text=_(
            'The date and time the file was created.'
        )
    )

    status = EnumField(
        SiteFileUploadStatus,
        default=SiteFileUploadStatus.UNPUBLISHED,
        null=False,
        blank=True,
        db_index=True,
        help_text=_(
            'The status of the file. This will also depend on what type the '
            'file is.'
        )
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_(
            'The user that uploaded the file.'
        )
    )

    # context generated at the time of upload - will be added to upload page
    # rendering for the file.
    context = compat.JSONField(
        null=False,
        blank=True,
        default=dict,
        encoder=DefaultToStrEncoder
    )

    description = models.TextField(
        blank=True,
        default='',
        help_text=_('A description of what this file is (optional).')
    )

    direction = EnumField(
        CardinalDirection,
        blank=True,
        default=None,
        null=True,
        help_text=_(
            'For images taken at the site, this is the cardinal direction the '
            'camera was pointing towards.'
        )
    )

    objects = SiteFileUploadManager.from_queryset(SiteFileUploadQuerySet)()

    def save(self, *args, **kwargs):
        self._discover_type()
        # if this is an image, attempt to pull the real timestamp out of the
        # meta data
        if not self.created and self.file_type == SLMFileType.SITE_IMAGE:
            tags = get_exif_tags(self.file.open('rb'))
            for tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                if tag in tags:
                    try:
                        self.created = datetime.strptime(
                            tags[tag],
                            '%Y:%m:%d %H:%M:%S'
                        )
                    except ValueError:
                        try:
                            self.created = parser.parse(tags[tag])
                        except parser.ParserError:
                            pass

                    if self.created:
                        if is_naive(self.created):
                            self.created = make_aware(self.created, utc)
                        break
        return super().save(*args, **kwargs)

    @property
    def link(self):
        return reverse(
            'slm:download_attachment',
            kwargs={'site': self.site.name, 'pk': self.pk}
        )

    @property
    def thumbnail_link(self):
        return reverse(
            'slm:download_attachment_thumbnail',
            kwargs={'site': self.site.name, 'pk': self.pk}
        )

    class Meta:
        ordering = ('-timestamp',)
        verbose_name_plural = 'Site File Uploads'


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
        related_name='logentries'
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        null=False,
        blank=True,
        db_index=True
    )

    # this is the timestamp of the data change which may be different than
    # the timestamp on the LogEntry, for instance in the event of a publish
    epoch = models.DateTimeField(
        null=False,
        blank=True,
        db_index=True
    )

    type = EnumField(LogEntryType, null=False, blank=False)

    site = models.ForeignKey(
        'slm.Site',
        on_delete=models.CASCADE,
        null=True,
        default=None,
        blank=True
    )

    site_log_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='logentries',
        null=True,
        default=None,
        blank=True
    )
    site_log_id = models.PositiveIntegerField(
        null=True,
        default=None,
        blank=True
    )
    site_log_object = GenericForeignKey('site_log_type', 'site_log_id')

    ip = models.GenericIPAddressField(null=True, default=None, blank=True)

    objects = LogEntryManager.from_queryset(LogEntryQuerySet)()

    @property
    def target(self):
        if self.type == LogEntryType.NEW_SITE:
            return self.site.name
        if self.site_log_type:
            if issubclass(self.site_log_type.model_class(), SiteSubSection):
                return self.site_log_type.model_class().subsection_name()
            elif issubclass(self.site_log_type.model_class(), SiteSection):
                return self.site_log_type.model_class().section_name()
            return self.site_log_type.verbose_name
        return ''

    def __str__(self):
        return f'({self.user.name or self.user.email if self.user else ""}) ' \
               f'[{self.timestamp}]: {self.type} -> {self.target}'

    class Meta:
        indexes = [
            models.Index(fields=["site_log_type", "site_log_id"]),
        ]
        ordering = ('-timestamp',)
