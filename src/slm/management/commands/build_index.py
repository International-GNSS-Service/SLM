"""
Under normal operations, each time a station's information is published, a new point
in time index is created and logs are serialized in all of the supported formats at
that index. If for whatever reason, those logs were not generated or the indexed
archived of site logs becomes stale you may run this command to generate indexed site
log files of the specified formats.

.. warning::

    This will not regenerate the historical index, but only files from the current
    database state.
"""

import typing as t

from django.db import transaction
from django.utils.translation import gettext as _
from django_typer.completers import these_strings
from django_typer.management import TyperCommand
from tqdm import tqdm
from typer import Option
from typing_extensions import Annotated

from slm.defines import SiteLogFormat, SiteLogStatus
from slm.models import ArchiveIndex, Site


class Command(TyperCommand):
    help = _(
        "Update the site index from the current data. This will generate new "
        "serialized files for all published data that is not up to date in the "
        "index of archived site log files."
    )
    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        "version",
        "pythonpath",
        "settings",
    }

    formats: t.List[t.Union[str, SiteLogFormat]] = list(
        set([fmt.ext for fmt in SiteLogFormat])
    )

    def handle(
        self,
        rebuild: Annotated[
            bool,
            Option(
                "--rebuild",
                help="Clear the existing index first. WARNING: cannot be undone.",
            ),
        ] = False,
        formats: Annotated[
            t.List[
                str
            ],  # list of SiteLogFormat's does not work for some upstream reason
            Option(
                "--format",
                metavar="FORMAT",
                help=_("Only import any site logs of the specified format(s)."),
                shell_complete=these_strings(set([fmt.ext for fmt in SiteLogFormat])),
            ),
        ] = formats,
    ):
        self.formats = [SiteLogFormat(fmt) for fmt in formats]
        if SiteLogFormat.LEGACY in self.formats:
            self.formats.insert(0, SiteLogFormat.ASCII_9CHAR)

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

            sites = Site.objects.public().filter(status=SiteLogStatus.PUBLISHED)
            # build from current data
            with tqdm(
                total=sites.count(), desc="Indexing", unit="sites", postfix={"site": ""}
            ) as p_bar:
                for site in sites:
                    p_bar.set_postfix({"site": site.name})
                    ArchiveIndex.objects.add_index(site=site, formats=self.formats)
                    p_bar.update(n=1)
