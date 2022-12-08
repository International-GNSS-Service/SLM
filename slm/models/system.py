from django.db import models
from django.conf import settings
from django.utils.translation import gettext as _
from slm.defines import AlertLevel
from django_enum import EnumField
from django.db.models import Q
from slm.defines import (
    AntennaReferencePoint,
    AntennaFeatures,
    EquipmentState,
    SLMFileType,
    SiteLogFormat,
    LogEntryType,
    SiteFileUploadStatus,
    CardinalDirection
)
from slm.models.sitelog import (
    SiteSubSection,
    SiteSection,
    DefaultToStrEncoder
)
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from slm.models import compat
import os
from pathlib import Path


class AgencyManager(models.Manager):
    pass


class AgencyQuerySet(models.QuerySet):

    def membership(self, user):
        """Get the agency(s) this user is a member of."""
        if user.is_superuser:
            return self
        if user.agency:
            return self.filter(pk__in=[user.agency.pk])
        return self.none()


class Agency(models.Model):
    id = models.AutoField(primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    shortname = models.CharField(max_length=20, blank=True, null=True)
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


class SatelliteSystem(models.Model):

    name = models.CharField(
        primary_key=True,
        max_length=16,
        null=False,
        blank=False
    )

    order = models.IntegerField(
        null=False,
        default=0,
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = _('Satellite Systems')
        ordering = ('order',)


class AlertManager(models.Manager):
    pass


class AlertQuerySet(models.QuerySet):

    def for_user(self, user):
        if user.is_authenticated:
            from slm.models.sitelog import Site
            qry = Q(user=user) | Q(site__in=Site.objects.editable_by(user))
            if getattr(user, 'agency', None):
                qry |= Q(agency=user.agency)
            return self.filter(qry)
        return self.none()


class Alert(models.Model):

    header = models.CharField(
        max_length=100,
        null=False,
        default='',
        help_text=_('A short description of the alert.')
    )
    detail = models.TextField(
        blank=True,
        null=False,
        default='',
        help_text=_('Longer description containing details of the alert.')
    )

    level = EnumField(AlertLevel, null=False, blank=False, db_index=True)

    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text=_('The time the alert was created.'),
        db_index=True
    )

    sticky = models.BooleanField(
        default=False,
        blank=True,
        help_text=_(
            'Do not allow target users to clear this alert, only admins may '
            'clear.'
        )
    )

    expires = models.DateTimeField(
        null=True,
        default=None,
        blank=True,
        help_text=_('Automatically remove this alert after this time.')
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_('Only this user will see this alert.'),
        related_name='alerts'
    )

    site = models.ForeignKey(
        'slm.Site',
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_(
            'Only users with access to this site will see this alert.'
        ),
        related_name='alerts'
    )

    agency = models.ForeignKey(
        'slm.Agency',
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_('Only members of this agency will see this alert.'),
        related_name='alerts'
    )

    objects = AlertManager.from_queryset(AlertQuerySet)()

    def __str__(self):
        return self.header

    class Meta:
        managed = True
        ordering = ('-timestamp',)


class Network(models.Model):

    name = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        db_index=True
    )

    sites = models.ManyToManyField('slm.Site', related_name='networks')

    def __str__(self):
        return self.name


class ReviewRequestManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related(
            'site',
            'requester',
            'requester__agency',
            'site__owner',
            'site__owner__agency',
            'site__last_user',
            'site__last_user__agency'
        ).prefetch_related(
            'site__agencies',
            'site__networks'
        )


class ReviewRequestQuerySet(models.QuerySet):

    def editable_by(self, user):
        from slm.models.sitelog import Site
        return self.filter(
            site__in=Site.objects.editable_by(user)
        )


class ReviewRequest(models.Model):

    site = models.OneToOneField(
        'slm.Site',
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='review_request'
    )

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        blank=True
    )

    objects = ReviewRequestManager.from_queryset(ReviewRequestQuerySet)()


class Manufacturer(models.Model):

    name = models.CharField(max_length=45, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Equipment(models.Model):

    model = models.CharField(
        max_length=50,
        unique=True,
        help_text=_(
            'The alphanumeric model of designation of this equipment.'
        ),
        db_index=True
    )

    description = models.CharField(
        max_length=500,
        help_text=_('The equipment characteristics.')
    )

    state = EnumField(
        EquipmentState,
        db_index=True,
        help_text=_('Is this equipment in active production?')
    )

    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        null=True,
        default=None,
        blank=True,
        help_text=_('The manufacturing organization.')
    )

    def __str__(self):
        return self.model

    class Meta:
        abstract = True
        ordering = ('model',)


class Antenna(Equipment):

    graphic = models.TextField(blank=True, null=False, default='')

    reference_point = EnumField(
        AntennaReferencePoint,
        blank=True,
        default=None,
        null=True,
        verbose_name=_('Antenna Reference Point'),
        help_text=_(
            'Locate your antenna in the file '
            'https://files.igs.org/pub/station/general/antenna.gra. Indicate '
            'the three-letter abbreviation for the point which is indicated '
            'equivalent to ARP for your antenna. Contact the Central Bureau if'
            ' your antenna does not appear. Format: (BPA/BCR/XXX from '
            'antenna.gra; see instr.)'
        )
    )

    features = EnumField(
        AntennaFeatures,
        blank=True,
        default=None,
        null=True,
        verbose_name=_('Antenna Features'),
        help_text=_('NOM/RXC/XXX from "antenna.gra"; see NRP abbreviations.')
    )

    verified = models.BooleanField(
        default=False,
        help_text=_('Has this antenna type been verified to be accurate?')
    )

    @property
    def full(self):
        return f'{self.model} {self.reference_point.label} ' \
               f'{self.features.label}'

    def __str__(self):
        return self.model


class Receiver(Equipment):
    pass


class Radome(Equipment):
    pass


def site_upload_path(instance, filename):
    """
     file will be saved to:
        MEDIA_ROOT/uploads/<9-char site name>/year/month/day/filename
        MEDIA_ROOT/uploads/<9-char site name>/filename
    """
    prefix = ''
    if instance.SUB_DIRECTORY:
        prefix = f'{instance.SUB_DIRECTORY}/'
    #return f'{prefix}{instance.site.name}/{instance.timestamp.year}/' \
    #       f'{instance.timestamp.month}/{instance.timestamp.day}/{filename}'
    return f'{prefix}{instance.site.name}/{filename}'


class SiteFile(models.Model):

    SUB_DIRECTORY = 'misc'

    site = models.ForeignKey(
        'slm.Site',
        on_delete=models.CASCADE,
        null=False,
        help_text=_('The site this file is attached to.')
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_('When the file was uploaded.')
    )

    file = models.FileField(
        upload_to=site_upload_path,
        null=False,
        help_text=_('A pointer to the uploaded file on disk.')
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
        if not self.mimetype:
            import mimetypes
            self.mimetype = mimetypes.guess_type(self.file.path)[0]
        if self.file_type is SLMFileType.ATTACHMENT:
            self.file_type, self.log_format = self.determine_type(
                self.file,
                self.mimetype
            )
        return super().save(*args, **kwargs)

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
            pass
        elif mimetype == SiteLogFormat.JSON.mimetype:
            pass
        elif mimetype.split('/')[0] == 'image':
            return SLMFileType.SITE_IMAGE, None

        return file_type, log_format

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

    def public(self):
        from slm.models.sitelog import Site
        return self.filter(
            status=SiteFileUploadStatus.PUBLISHED,
            site__in=Site.objects.public()
        )


class SiteFileUpload(SiteFile):

    SUB_DIRECTORY = 'uploads'

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=255,
        help_text=_('The name of the file.')
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

    class Meta:
        ordering = ('-timestamp',)


class RenderedSiteLog(SiteFile):

    SUB_DIRECTORY = 'logs'


class LogEntryManager(models.Manager):
    pass


class LogEntryQuerySet(models.QuerySet):

    def for_user(self, user):
        if user.is_superuser:
            return self
        return self.filter(site__agencies__in=[user.agency])


class LogEntry(models.Model):

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
