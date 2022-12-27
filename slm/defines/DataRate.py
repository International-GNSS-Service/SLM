from django_enum import IntegerChoices


class DataRate(IntegerChoices):

    DAILY     = 0, 'Daily'
    HOURLY    = 1, 'Hourly'
    HIGH_RATE = 2, 'High Rate'

    def __str__(self):
        return str(self.label)
