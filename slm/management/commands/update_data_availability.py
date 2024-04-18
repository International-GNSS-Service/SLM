"""
Update the data availability information for each station.
"""

import logging
from datetime import datetime, timedelta

from django.core.management import BaseCommand
from django.utils.timezone import now
from django.utils.translation import gettext as _

from igs_tools.defines import DataCenter
from igs_tools.directory import DirectoryListing
from slm.defines import DataRate, RinexVersion
from slm.models import DataAvailability, Site


class Command(BaseCommand):
    help = "Update the data availability information for each station."

    logger = logging.getLogger(__name__ + ".Command")

    LOOKBACK = 60  # 60 days

    UNHEALTHY = (now() - timedelta(days=30)).date()
    STALE = (now() - timedelta(days=10)).date()

    def add_arguments(self, parser):
        parser.add_argument(
            "stations",
            metavar="S",
            nargs="*",
            type=str,
            help=_(
                "The station(s) to update, if unspecified, update data "
                "availability information for all of them."
            ),
        )

        parser.add_argument(
            "--username",
            dest="username",
            type=str,
            help=_("Username to login to ftp."),
            default="",
        )

        parser.add_argument(
            "--password",
            dest="password",
            type=str,
            help=_("Password to login to ftp."),
            default="",
        )

        parser.add_argument(
            "-l",
            "--lookback",
            dest="lookback",
            type=int,
            default=self.LOOKBACK,
            help=_(
                "The number of days into the past to look. Default: {lookback}"
            ).format(lookback=self.LOOKBACK),
        )

        # todo remove this after testing?
        parser.add_argument(
            "-c",
            "--clear",
            dest="clear",
            action="store_true",
            default=False,
            help=_(
                "Clear all existing DataAvailability information. "
                "Careful - this cannot be undone."
            ),
        )

        parser.add_argument(
            "--rate",
            dest="data_rates",
            action="append",
            default=[],
            type=DataRate,
            choices=[rate.slug for rate in DataRate],
            help=f"The data rates to update availability for. "
            f"Default: {[rt.slug for rt in DirectoryListing.data_rates]}",
        )

        parser.add_argument(
            "--rinex",
            dest="rinex_versions",
            action="append",
            default=[],
            type=RinexVersion,
            choices=[ver.slug for ver in RinexVersion.major_versions()],
            help=f"The rinex versions to update availability for. "
            f"Default: "
            f"{[ver.slug for ver in DirectoryListing.rinex_versions]}",
        )

        parser.add_argument(
            "--center",
            dest="data_centers",
            action="append",
            default=[],
            type=DataCenter,
            choices=[str(dc) for dc in DataCenter],
            help=f"The data centers to look for data at. Default: "
            f"{[str(dc) for dc in DirectoryListing.data_centers]}",
        )

    def handle(self, *args, **options):
        availability = {}
        unrecognized = set()
        for listing in DirectoryListing(
            stations=options["stations"],
            start=now(),
            end=now() - timedelta(days=options["lookback"]),
            username=options["username"],
            password=options["password"],
            data_rates=options["data_rates"],
            rinex_versions=options["rinex_versions"],
            data_centers=options["data_centers"],
        ):
            if listing.file_type not in {"d", "O"}:
                continue
            try:
                avail, created = DataAvailability.objects.get_or_create(
                    site=Site.objects.get(name__istartswith=listing.station),
                    rinex_version=listing.rinex_version,
                    rate=listing.data_rate,
                    last=(
                        listing.date.date()
                        if isinstance(listing.date, datetime)
                        else listing.date
                    ),
                )
            except Site.DoesNotExist:
                unrecognized.add(listing.station)
                continue
            availability.setdefault(avail.site.name, avail.last)
            if availability[avail.site.name] < avail.last:
                availability[avail.site.name] = avail.last

        unhealthy = []
        stale = []
        healthy = []
        for station, last in availability.items():
            if last < self.UNHEALTHY:
                unhealthy.append((station, last))
            elif last < self.STALE:
                stale.append((station, last))
            else:
                healthy.append((station, last))

        for station, last in healthy:
            self.stdout.write(self.style.SUCCESS(f"{station} {last}"))
        for station, last in stale:
            self.stdout.write(self.style.WARNING(f"{station} {last}"))
        for station, last in unhealthy:
            self.stdout.write(self.style.ERROR(f"{station} {last}"))

        self.stdout.write(self.style.WARNING(f"Ignored {len(unrecognized)} stations."))
        self.stdout.write(self.style.SUCCESS(f"Updated {len(availability)} stations."))
