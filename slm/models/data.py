from django.db import models
from slm.defines import (
    RinexVersion,
    DataRate
)
from django_enum import EnumField


class DataAvailability(models.Model):
    site = models.ForeignKey('slm.Site', on_delete=models.CASCADE)
    rinex_version = EnumField(RinexVersion, null=False, db_index=True)
    rate = EnumField(DataRate, null=False, db_index=True)
    last = models.DateTimeField(null=False, db_index=True)

    def __str__(self):
        return f'[{self.site}] ({self.rinex_version.label}) ' \
               f'{self.rate.label} {self.last}'

    class Meta:
        """
        TODO - should this be allowed to be a time series??
        """
        unique_together = (('site', 'rinex_version', 'rate'),)
        index_together = (('site', 'rinex_version', 'rate'),)
