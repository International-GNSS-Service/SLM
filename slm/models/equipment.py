from django.db import models
from django.utils.translation import gettext as _
from django_enum import EnumField
from slm.defines import (
    AntennaReferencePoint,
    AntennaFeatures,
    EquipmentState,
    AntennaCalibration
)


class SatelliteSystem(models.Model):

    name = models.CharField(
        primary_key=True,
        max_length=16,
        null=False,
        blank=False,
        db_index=True
    )

    order = models.IntegerField(
        null=False,
        default=0,
        blank=True,
        db_index=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = _('Satellite Systems')
        ordering = ('order',)


class Manufacturer(models.Model):

    name = models.CharField(max_length=45, unique=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Equipment(models.Model):

    API_RELATED_FIELD = 'model'

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
        ),
        db_index=True
    )

    features = EnumField(
        AntennaFeatures,
        blank=True,
        default=None,
        null=True,
        verbose_name=_('Antenna Features'),
        help_text=_('NOM/RXC/XXX from "antenna.gra"; see NRP abbreviations.'),
        db_index=True
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


class AntCal(models.Model):

    antenna = models.ForeignKey(
        Antenna,
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )

    radome = models.ForeignKey(
        Radome,
        blank=False,
        null=True,
        on_delete=models.CASCADE
    )

    calibration = EnumField(
        AntennaCalibration,
        blank=True,
        null=True,
        db_index=True
    )

    dazi = models.FloatField(blank=True, null=True, db_index=True)
    zen = models.FloatField(blank=True, null=True, db_index=True)

    class Meta:
        index_together = (('antenna', 'radome'),)
        unique_together = (('antenna', 'radome'),)
