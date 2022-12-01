from django.db import models
from django.conf import settings
from django.utils.translation import gettext as _
from slm.defines import AlertLevel
from django_enum import EnumField
from django.db.models import Q
from slm.defines import (
    AntennaReferencePoint,
    AntennaFeatures,
    EquipmentState
)
from django.contrib.auth import get_user_model


class AgencyManager(models.Manager):
    pass


class AgencyQuerySet(models.QuerySet):

    def membership(self, user):
        """Get the agency(s) this user is a member of."""
        if user.is_superuser:
            return self
        return self.filter(pk__in=[user.agency.pk])


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
            'from public exposure.')
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
        from slm.models.sitelog import Site
        return self.filter(
            Q(user=user) | Q(agency=user.agency) |
            Q(site__in=Site.objects.editable_by(user))
        )


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
