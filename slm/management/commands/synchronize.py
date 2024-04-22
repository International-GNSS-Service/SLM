"""
Update the data availability information for each station.
"""

import typing as t

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_typer import TyperCommand, model_parser_completer
from typer import Argument
from typing_extensions import Annotated

from slm.models import Site


class Command(TyperCommand):
    help = _(
        "Synchronize all denormalized data - that is data that is cached for "
        "performance reasons that may become out of sync if updates are "
        "performed outside of normal request/response cycles."
    )

    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        "version",
        "pythonpath",
        "settings",
    }

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
    ):
        with transaction.atomic():
            qry = Q()
            if sites:
                qry = Q(pk__in=[site.id for site in sites])
            Site.objects.filter(qry).synchronize_denormalized_state()
