"""
Update the data availability information for each station.
"""

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django_typer import TyperCommand
from tqdm import tqdm
from typer import Option
from typing_extensions import Annotated

from slm.defines import SiteLogStatus
from slm.models import ArchiveIndex, Site


class Command(TyperCommand):
    help = _(
        "Update the site index from the current data or rebuild from "
        "archives. Note - this will generate new serialized files for all"
        "published data that is not up to date in the archive."
    )
    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        "version",
        "pythonpath",
        "settings",
    }

    def handle(
        self,
        rebuild: Annotated[
            bool,
            Option(help="Clear the existing index first. WARNING: cannot be undone."),
        ] = False,
        archive: Annotated[
            bool,
            Option("--archive", "-a", help="Build index from the archive directory."),
        ] = False,
    ):
        with transaction.atomic():

            def yes(ipt):
                return ipt.lower() in {"y", "yes", "true", "continue"}

            if rebuild:
                if yes(
                    input(
                        _(
                            "WARNING: this will delete the current index. This cannot "
                            "be undone if you do not have an external archive! "
                            "Proceed? (Y/N): "
                        )
                    )
                ):
                    ArchiveIndex.objects.all().delete()
                else:
                    return

            if archive:
                # todo
                raise NotImplementedError("Rebuild from archive not implemented yet!")

            sites = Site.objects.public().filter(status=SiteLogStatus.PUBLISHED)
            # build from current data
            with tqdm(
                total=sites.count(), desc="Indexing", unit="sites", postfix={"site": ""}
            ) as p_bar:
                for site in sites:
                    p_bar.set_postfix({"site": site.name})
                    ArchiveIndex.objects.add_index(site=site)
                    p_bar.update(n=1)
