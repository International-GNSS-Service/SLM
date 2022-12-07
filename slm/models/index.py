"""
The Site Log models contain edit histories and a tree-like structure that
make complex queries (potentially) very slow. To remedy this the best and
really only option is to denormalize the data. All searchable site log fields
should be defined and indexed here.

Think of this record as a Materialized View that's defined in code to make
it RDBMS independent.

Denormalization introduces the potential for data inconsistency. If updates are
published and a corresponding SiteRecord is not created, search results will be
incorrect. This will not however break editing or site log serialization. In
the context of the rest of the software - this table should be treated as
a read-only index.

Extensions:

Extending software may want to include or change search fields. To do this a
new SiteRecord model should be created that extends from AbstractSiteRecord.
In settings the SLM_SITE_RECORD setting should be updated to:
'<app_label>.<model_class>'. For instance, the default is:

.. code-block:

    SLM_SITE_RECORD = 'slm.DefaultSiteRecord'

SiteRecord is never used directly in software, like with Django's swappable
user model, use a function that returns the configured model type:

.. code-block:

    from slm.models import get_record_model
    get_record_model()

"""
from django.db import models
from django.db.models import Q, OuterRef, Subquery, F
from django.utils.timezone import now
from slm.models.data import DataAvailability
from slm.models.system import (
    SiteFile,
    Antenna,
    Receiver,
    Radome,
    SatelliteSystem
)
from slm.defines import (
    FrequencyStandardType,
    ISOCountry,
    RinexVersion,
    SiteLogFormat,
    SLMFileType
)
from django_enum import EnumField
from django.db.models.functions import Now
from django.core.files.base import ContentFile


class SiteIndexManager(models.Manager):

    def add_index(self, site):
        existing = self.filter(site=site, begin=site.last_publish).first()
        if existing:
            return existing

        self.close_index(site)

        location = site.sitelocation_set.current(published=True)
        identification = site.siteidentification_set.current(published=True)
        antenna = site.siteantenna_set.current(published=True).filter(
            removed__isnull=True
        ).order_by('-installed').first()
        receiver = site.sitereceiver_set.current(published=True).filter(
            removed__isnull=True
        ).order_by('-installed').first()
        frequency = site.sitefrequencystandard_set.current(
            published=True
        ).filter(
            effective_end__isnull=True
        ).order_by('-effective_start').first()
        more_info = site.sitemoreinformation_set.current(published=True)

        new_index = self.create(
            site=site,
            begin=site.last_publish,
            end=None,
            latitude=location.latitude / 10000 if location else None,
            longitude=location.longitude / 10000 if location else None,
            elevation=location.elevation if location else None,
            city=location.city if location else '',
            country=location.country if location else '',
            antenna=antenna.antenna_type if antenna else None,
            radome=antenna.radome_type if antenna else None,
            receiver=receiver.receiver_type if receiver else None,
            serial_number=receiver.serial_number if receiver else '',
            firmware=receiver.firmware if receiver else '',
            frequency_standard=frequency.standard_type if frequency else None,
            domes_number=(
                identification.iers_domes_number if identification else None
            ),
            data_center=more_info.primary
        )
        if receiver:
            new_index.satellite_system.set(receiver.satellite_system.all())

        for log_format in SiteLogFormat:
            if log_format in {SiteLogFormat.GEODESY_ML, SiteLogFormat.JSON}:
                continue  # todo - remove
            ArchivedSiteLog.objects.from_site(site=site, log_format=log_format)

        return new_index

    def close_index(self, site):
        last = self.filter(site=site).filter(
            Q(begin__lte=site.last_publish) &
            Q(end__isnull=True) | Q(end__gt=site.last_publish)
        ).first()
        if last:
            last.end = site.last_publish
            last.save()


class SiteIndexQuerySet(models.QuerySet):

    def at_epoch(self, epoch=None):
        if epoch is None:
            epoch = now()
        return self.filter(
            Q(begin__lte=epoch) & (Q(end__gt=epoch) | Q(end__isnull=True))
        )

    def public(self):
        return self.filter(site__agencies__public=True)

    def availability(self):
        last_data_avail = DataAvailability.objects.filter(
            site=OuterRef('pk')
        ).order_by('-last')
        return self.annotate(
            last_data_time=Subquery(last_data_avail.values('last')[:1]),
            last_data=Now() - F('last_data_time'),
            last_rinex2=Subquery(
                last_data_avail.filter(
                    RinexVersion(2).major_q()
                ).values('last')[:1]),
            last_rinex3=Subquery(
                last_data_avail.filter(
                    RinexVersion(3).major_q()
                ).values('last')[:1]),
            last_rinex4=Subquery(
                last_data_avail.filter(
                    RinexVersion(4).major_q()
                ).values('last')[:1])
        )


class SiteIndex(models.Model):

    site = models.ForeignKey('slm.Site', on_delete=models.CASCADE, null=False)

    # the point in time at which this record begins being valid
    begin = models.DateTimeField(null=False, db_index=True)

    # the point in time at which this record stops being valid
    end = models.DateTimeField(null=True, db_index=True)

    latitude = models.FloatField(db_index=True, null=True)
    longitude = models.FloatField(db_index=True, null=True)
    elevation = models.FloatField(db_index=True, null=True)

    city = models.CharField(default='', db_index=True, max_length=100)
    country = EnumField(
        ISOCountry,
        null=True,
        db_index=True,
        max_length=255,
        strict=False
    )

    antenna = models.ForeignKey(Antenna, on_delete=models.PROTECT, null=True)
    radome = models.ForeignKey(Radome, on_delete=models.PROTECT, null=True)
    receiver = models.ForeignKey(Receiver, on_delete=models.PROTECT, null=True)

    serial_number = models.CharField(db_index=True, max_length=100)
    firmware = models.CharField(db_index=True, max_length=100)

    frequency_standard = EnumField(
        FrequencyStandardType,
        null=True,
        db_index=True,
        strict=False,
        max_length=100
    )

    domes_number = models.CharField(db_index=True, max_length=100)

    satellite_system = models.ManyToManyField(SatelliteSystem)

    data_center = models.CharField(db_index=True, max_length=100)

    objects = SiteIndexManager.from_queryset(SiteIndexQuerySet)()

    class Meta:
        ordering = ('-begin',)
        index_together = (('begin', 'end'), ('site', 'begin', 'end'),)
        unique_together = (('site', 'begin'), ('site', 'end'))


class ArchivedSiteLogManager(models.Manager):

    def from_site(self, site, log_format=SiteLogFormat.LEGACY, epoch=None):
        index = SiteIndex.objects.filter(site=site).at_epoch(
            epoch=epoch
        ).first()
        if index:
            file = index.files.filter(log_format=log_format).first()
            if file:
                return file

            from slm.api.serializers import SiteLogSerializer
            archive_file = ArchivedSiteLog.objects.create(
                site=site,
                log_format=log_format,
                index=index,
                timestamp=index.begin,
                mimetype=log_format.mimetype,
                file_type=SLMFileType.SITE_LOG,
                name=site.get_filename(log_format=log_format, epoch=epoch)
            )
            archive_file.file.save(
                site.get_filename(log_format=log_format, epoch=epoch),
                ContentFile(
                    SiteLogSerializer(instance=site, epoch=epoch).format(
                        log_format
                    )
                )
            )

        return None


class ArchivedSiteLogQuerySet(models.QuerySet):
    pass


class ArchivedSiteLog(SiteFile):

    SUB_DIRECTORY = 'archive'

    index = models.ForeignKey(
        SiteIndex,
        on_delete=models.CASCADE,
        related_name='files'
    )

    name = models.CharField(max_length=50)

    objects = ArchivedSiteLogManager.from_queryset(ArchivedSiteLogQuerySet)()

    class Meta:
        unique_together = ('index', 'log_format')
