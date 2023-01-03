from django_enum import IntegerChoices


class DataRate(IntegerChoices):

    DAILY     = 1, 'Daily'
    HOURLY    = 2, 'Hourly'
    HIGH_RATE = 3, 'High Rate'

    def __str__(self):
        return str(self.label)
