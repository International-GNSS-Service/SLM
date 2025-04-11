from django.db import models
from django_enum import EnumField

from slm.defines import DataRate, RinexVersion


class DataAvailability(models.Model):
    site = models.ForeignKey("slm.Site", on_delete=models.CASCADE, related_name="data")

    rinex_version = EnumField(RinexVersion, null=True, default=True, db_index=True)
    rate = EnumField(DataRate, null=True, default=True, db_index=True)
    last = models.DateField(null=False, db_index=True)

    data_centers = models.ManyToManyField("slm.DataCenter", blank=True)

    def __str__(self):
        return (
            f"[{self.site}] ({self.rinex_version.label}) {self.rate.label} {self.last}"
        )

    class Meta:
        unique_together = (("site", "rinex_version", "rate", "last"),)
        indexes = [
            models.Index(fields=("site", "rinex_version", "rate", "last")),
            models.Index(fields=("site", "rinex_version", "rate")),
            models.Index(fields=("site", "rinex_version")),
            models.Index(fields=("site", "last")),
            models.Index(fields=("site", "rinex_version", "last")),
        ]


class DataCenter(models.Model):
    name = models.CharField(max_length=255, unique=True)

    agency = models.ForeignKey(
        "slm.Agency",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="data_centers",
    )

    url = models.URLField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    ftp = models.URLField(max_length=255, unique=True)
    ftp_user = models.CharField(max_length=255, blank=True)
    ftp_password = models.CharField(max_length=255, blank=True)
    ftp_root = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name = "Data Center"
        verbose_name_plural = "Data Centers"
