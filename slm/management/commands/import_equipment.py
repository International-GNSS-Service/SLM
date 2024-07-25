"""
Station equipment including Antennas, Radomes and Receivers are coded by IGS and
those standard codes are used to uniquely identify equipment in site log files.

The full IGS change log for equipment codes is recorded in rcvr_ant.tab_.

The SLM stores these codes in database tables, so it is possible to instantiate an
SLM with a different set of equipment codes. This command can be used to load codes
from another SLM or from the IGS by default:

    * **antennas**: https://network.igs.org/api/public/antenna/
    * **receivers**: https://network.igs.org/api/public/receiver/
    * **radomes**: https://network.igs.org/api/public/radome/
    * **manufacturers**: https://network.igs.org/api/public/manufacturer/

.. tip::

    **import_equipment** can be run routinely to synchronize with upstream equipment
    sources. No equipment will be removed if any site logs reference it in the database.
"""

import typing as t

import requests
from django.db.models import Q
from django.utils.translation import gettext as _
from django_typer.completers import these_strings
from django_typer.management import TyperCommand, command, initialize
from typer import Context, Option
from typing_extensions import Annotated

from slm.defines import EquipmentState
from slm.models.equipment import Antenna, Manufacturer, Radome, Receiver


class Command(TyperCommand, rich_markup_mode="markdown", chain=True):
    help = _(
        "Import equipment (Antennas, Receivers and Radomes). Imports are made from "
        "the IGS public network API by default. You may periodically run this to "
        "synchronize with external equipment sources. These codings are used to "
        "standardize references to equipment in site logs. For a full change log of "
        "equipment encodings used by IGS, see: "
        "https://files.igs.org/pub/station/general/rcvr_ant.tab"
    )

    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        "version",
        "pythonpath",
        "settings",
    }

    remove: bool = False
    synchronize: bool = True
    slm: t.Optional[str] = None
    states: t.List[t.Union[str, EquipmentState]] = [EquipmentState.ACTIVE.name]

    manufacturers: t.Set[Manufacturer]
    manufacturers_added: t.Set[Manufacturer]

    antennas: t.Set[Antenna]
    antennas_added: t.Set[Antenna]

    receivers: t.Set[Receiver]
    receivers_added: t.Set[Receiver]

    radomes: t.Set[Radome]
    radomes_added: t.Set[Radome]

    @property
    def params(self):
        """Global equipment request params"""
        return {"state": [st.value for st in self.states]}

    @initialize(invoke_without_command=True)
    def init(
        self,
        ctx: Context,
        remove: Annotated[
            bool,
            Option(
                "--remove",
                help=_(
                    "Remove any equipment from the database not present in sources."
                ),
            ),
        ] = remove,
        no_synchronize: Annotated[
            bool,
            Option(
                "--no-synchronize",
                help=_(
                    "Do not synchronize ancillary equipment meta data with source(s)."
                ),
            ),
        ] = synchronize,
        slm: Annotated[
            str,
            Option(
                help=_(
                    "The url to the SLM to pull equipment data from (if different than source defaults)."
                )
            ),
        ] = "https://network.igs.org",
        states: Annotated[
            t.List[
                str
            ],  # list of SiteLogFormat's does not work for some upstream reason
            Option(
                "--state",
                metavar="STATE",
                help=_("Only import equipment from these specified state(s)."),
                shell_complete=these_strings([st.name for st in EquipmentState]),
            ),
        ] = states,
    ):
        self.remove = remove
        self.synchronize = not no_synchronize
        self.slm = slm
        self.states = [EquipmentState(st) for st in states]
        self.manufacturers = set()
        self.manufacturers_added = set()
        self.antennas = set()
        self.antennas_added = set()
        self.receivers = set()
        self.receivers_added = set()
        self.radomes = set()
        self.radomes_added = set()

        if not ctx.invoked_subcommand:
            for cmd in [cmd for cmd in self.get_subcommand().children.values()]:
                cmd()

    def get_manufacturer(self, item):
        manufacturer, created = Manufacturer.objects.get_or_create(
            name=item.get("manufacturer", item)
        )
        self.manufacturers.add(manufacturer)
        if created:
            self.manufacturers_added.add(manufacturer)
        return manufacturer

    @command(help=_("Import manufacturers."))
    def manufacturers(
        self,
        sources: Annotated[
            t.List[str],
            Option(
                "--source", "-s", help=_("The source(s) to import manufacturers from.")
            ),
        ] = ["{slm}/api/public/manufacturer/"],
    ):
        sources = [src.format(slm=self.slm) for src in sources]
        for src in sources:
            manufacturers = requests.get(src, json=True).json()
            for entry in manufacturers:
                manufacturer, created = (
                    Manufacturer.objects.update_or_create
                    if self.synchronize
                    else Manufacturer.objects.get_or_create
                )(
                    name=entry["name"],
                    defaults={
                        "full_name": entry.get("full_name", ""),
                        "url": entry.get("url", None),
                    },
                )
                self.manufacturers.add(manufacturer)
                if created:
                    self.manufacturers_added.add(manufacturer)

        self.secho(
            _("Added {added} manufacturers from {sources}.").format(
                added=len(self.manufacturers_added),
                sources=sources[0] if len(sources) == 1 else sources,
            ),
            fg="green",
        )

        if self.remove:
            to_delete = Manufacturer.objects.filter(
                ~Q(id__in=[mf.id for mf in self.manufacturers])
            )
            num_to_delete = to_delete.count()
            if num_to_delete:
                to_delete.delete()
                self.secho(f"Removed {num_to_delete} manufacturers.", fg="red")

    @command(help=_("Import antennas."))
    def antennas(
        self,
        sources: Annotated[
            t.List[str],
            Option("--source", "-s", help=_("The source(s) to import antennas from.")),
        ] = ["{slm}/api/public/antenna/"],
    ):
        replacements = {}
        sources = [src.format(slm=self.slm) for src in sources]
        for src in sources:
            antennas = requests.get(src, params=self.params).json()
            for entry in antennas:
                antenna, created = (
                    Antenna.objects.update_or_create
                    if self.synchronize
                    else Antenna.objects.get_or_create
                )(
                    model=entry["model"],
                    defaults={
                        "description": entry.get("description", ""),
                        "state": EquipmentState(
                            entry.get("state", EquipmentState.ACTIVE)
                        ),
                        "features": entry.get("features", None),
                        "reference_point": entry.get("reference_point", None),
                        "graphic": entry.get("graphic", ""),
                    },
                )
                replaced = entry.get("replaced", [])
                if replaced:
                    replacements[antenna] = replaced
                self.antennas.add(antenna)
                if created:
                    self.antennas_added.add(antenna)

        self.secho(
            _("Added {added} antennas from {sources}.").format(
                added=len(self.antennas_added),
                sources=sources[0] if len(sources) == 1 else sources,
            ),
            fg="green",
        )

        for ant, replaced in replacements.items():
            ant.replaced.set(Antenna.objects.filter(model__in=replaced))

        if self.remove:
            to_delete = Antenna.objects.filter(
                ~Q(id__in=[ant.id for ant in self.antennas])
            )
            num_to_delete = to_delete.count()
            if num_to_delete:
                to_delete.delete()
                self.secho(f"Removed {num_to_delete} antennas.", fg="red")

    @command(help=_("Import receivers."))
    def receivers(
        self,
        sources: Annotated[
            t.List[str],
            Option("--source", "-s", help=_("The source(s) to import receivers from.")),
        ] = ["{slm}/api/public/receiver/"],
    ):
        replacements = {}
        sources = [src.format(slm=self.slm) for src in sources]
        for source in sources:
            source = source.format(slm=self.slm)
            receivers = requests.get(source, params=self.params).json()
            for entry in receivers:
                receiver, created = (
                    Receiver.objects.update_or_create
                    if self.synchronize
                    else Receiver.objects.get_or_create
                )(
                    model=entry["model"],
                    defaults={
                        "description": entry.get("description", ""),
                        "state": EquipmentState(
                            entry.get("state", EquipmentState.ACTIVE)
                        ),
                    },
                )

                replaced = entry.get("replaced", [])
                if replaced:
                    replacements[receiver] = replaced

                self.receivers.add(receiver)
                if created:
                    self.receivers_added.add(receiver)

        self.secho(
            _("Added {added} receivers from {sources}.").format(
                added=len(self.receivers_added),
                sources=sources[0] if len(sources) == 1 else sources,
            ),
            fg="green",
        )

        for ant, replaced in replacements.items():
            ant.replaced.set(Receiver.objects.filter(model__in=replaced))

        if self.remove:
            to_delete = Receiver.objects.filter(
                ~Q(id__in=[rec.id for rec in self.receivers])
            )
            num_to_delete = to_delete.count()
            if num_to_delete:
                to_delete.delete()
                self.secho(f"Removed {num_to_delete} receivers.", fg="red")

    @command(help=_("Import radomes."))
    def radomes(
        self,
        sources: Annotated[
            t.List[str],
            Option("--source", "-s", help=_("The source(s) to import radomes from.")),
        ] = ["{slm}/api/public/radome/"],
    ):
        replacements = {}
        sources = [src.format(slm=self.slm) for src in sources]
        for source in sources:
            source = source.format(slm=self.slm)
            radomes = requests.get(source, params=self.params).json()
            for entry in radomes:
                radome, created = (
                    Radome.objects.update_or_create
                    if self.synchronize
                    else Radome.objects.get_or_create
                )(
                    model=entry["model"],
                    defaults={
                        "description": entry.get("description", ""),
                        "state": EquipmentState(
                            entry.get("state", EquipmentState.ACTIVE)
                        ),
                    },
                )

                replaced = entry.get("replaced", [])
                if replaced:
                    replacements[radome] = replaced

                self.radomes.add(radome)
                if created:
                    self.radomes_added.add(radome)

        self.secho(
            _("Added {added} radomes from {sources}.").format(
                added=len(self.radomes_added),
                sources=sources[0] if len(sources) == 1 else sources,
            ),
            fg="green",
        )

        for ant, replaced in replacements.items():
            ant.replaced.set(Radome.objects.filter(model__in=replaced))

        if self.remove:
            to_delete = Radome.objects.filter(
                ~Q(id__in=[rad.id for rad in self.radomes])
            )
            num_to_delete = to_delete.count()
            if num_to_delete:
                to_delete.delete()
                self.secho(f"Removed {num_to_delete} radomes.", fg="red")
