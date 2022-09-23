from django.db import models
from slm.defines import (
    RinexVersion,
    DataRate
)
from django_enum import EnumField


class DataAvailability(models.Model):

    site = models.ForeignKey('slm.Site', on_delete=models.CASCADE)
    rinex_version = EnumField(RinexVersion, null=False)
    rate = EnumField(DataRate, null=False)
    last = models.DateTimeField(null=False)

    class Meta:
        unique_together = (('site', 'rinex_version', 'rate'),)
