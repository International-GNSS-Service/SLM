"""
Update the data availability information for each station.
"""

import typing as t
from datetime import datetime, timedelta

from django.utils.timezone import now
from django.utils.translation import gettext as _
from django_typer.management import TyperCommand, model_parser_completer
from typer import Argument, Option
from typing_extensions import Annotated

from igs_tools.defines import DataCenter
from igs_tools.directory import DirectoryListing
from slm.defines import DataRate, RinexVersion
from slm.management.commands import EnumParser
from slm.models import DataAvailability, Site


class Command(TyperCommand):
    help = _("Update the data availability information for each station.")

    LOOKBACK = 60  # 60 days

    UNHEALTHY = (now() - timedelta(days=30)).date()
    STALE = (now() - timedelta(days=10)).date()

    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        "version",
        "pythonpath",
        "settings",
        "skip-checks",
    }
    requires_migrations_checks = False
    requires_system_checks = []

    def handle(
        self,
        sites: Annotated[
            t.Optional[t.List[Site]],
            Argument(
                **model_parser_completer(
                    Site, lookup_field="name", case_insensitive=True
                ),
                help=_(
                    "The station(s) to update, if unspecified, update data "
                    "availability information for all of them."
                ),
            ),
        ] = None,
        username: Annotated[str, Option(help=_("Username to login to ftp."))] = "",
        password: Annotated[
            str,
            Option(
                prompt=True,
                prompt_required=False,
                hide_input=True,
                help=_("Password to login to ftp."),
            ),
        ] = "",
        lookback: Annotated[
            int,
            Option(
                "-l", "--lookback", help=_("The number of days into the past to look.")
            ),
        ] = LOOKBACK,
        data_rates: Annotated[
            t.Optional[t.List[DataRate]],
            Option(
                "--rate",
                parser=EnumParser(DataRate, field="slug"),
                help=_(
                    "Restrict the data rates to update availability for. {rates}"
                ).format(rates=", ".join([rate.slug for rate in DataRate])),
            ),
        ] = [rate.slug for rate in DirectoryListing.data_rates],
        rinex_versions: Annotated[
            t.Optional[t.List[RinexVersion]],
            Option(
                "--rinex",
                parser=EnumParser(RinexVersion, field="slug"),
                help=_(
                    "Restrict rinex versions to update availability for ({versions})."
                ).format(
                    versions=", ".join(
                        [ver.slug for ver in RinexVersion.major_versions()]
                    )
                ),
            ),
        ] = [ver.slug for ver in DirectoryListing.rinex_versions],
        data_centers: Annotated[
            t.Optional[t.List[DataCenter]],
            Option(
                "--center",
                parser=EnumParser(DataCenter, field="label"),
                help=_(
                    "Restrict data centers to update availability for ({centers})."
                ).format(centers=", ".join([str(dc) for dc in DataCenter])),
            ),
        ] = [dc for dc in DirectoryListing.data_centers],
    ):
        availability = {}
        unrecognized = set()
        for listing in DirectoryListing(
            stations=[site.name for site in sites or Site.objects.active()],
            start=now(),
            end=now() - timedelta(days=lookback),
            username=username,
            password=password,
            data_rates=data_rates or [],
            rinex_versions=rinex_versions or [],
            data_centers=data_centers or [],
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

        self.stdout.write(
            self.style.WARNING(
                _("Ignored {unrecognized} stations.").format(
                    unrecognized=len(unrecognized)
                )
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                _("Updated {availability} stations.").format(
                    availability=len(availability)
                )
            )
        )
