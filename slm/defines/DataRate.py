from datetime import date

from django_enum import IntegerChoices
from enum_properties import p, s


class DataRate(IntegerChoices):

    DAILY     = 0, 'Daily'
    HOURLY    = 1, 'Hourly'
    HIGH_RATE = 2, 'High Rate'

    def __str__(self):
        return self.label
