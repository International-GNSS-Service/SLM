"""
The SLM supports pluggable validation logic for all site log sections and fields. Since
this logic is configuration specific, it may change, diverging from the validation flags
recorded against the previous validation configuration in the database.

Run this command to run all validation routines against all current site log fields
in the database.
"""

import typing as t

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils.translation import gettext as _
from django_typer.management import TyperCommand, model_parser_completer
from tqdm import tqdm
from typer import Argument, Option
from typing_extensions import Annotated

from slm.defines import SiteLogStatus
from slm.models import GeodesyMLInvalid, Site


class Command(TyperCommand):
    help = _(
        "Validate and update status of head state of all existing site logs. "
        "This might be necessary to run if the validation configuration is "
        "updated."
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
                help=_("The name of the site(s). Default - all sites."),
            ),
        ] = None,
        clear: Annotated[
            bool, Option("--clear", help=_("Clear existing validation flags."))
        ] = False,
        schema: Annotated[
            bool,
            Option(
                "--schema",
                help=_(
                    "Also perform validation of generated GeodesyML files "
                    "against the latest schema."
                ),
            ),
        ] = False,
        all: Annotated[
            bool,
            Option(
                "--all",
                help=_("Validate all sites, not just the currently public sites."),
            ),
        ] = False,
    ):
        from slm.validators import set_bypass

        set_bypass(True)
        invalid = 0
        valid = 0
        critical = 0
        old_flag_count = Site.objects.aggregate(Sum("num_flags"))["num_flags__sum"]
        with transaction.atomic():
            sites = sites or Site.objects.all()
            if not all:
                sites = Site.objects.filter(
                    Q(pk__in=[site.pk for site in sites])
                    & Q(status__in=[SiteLogStatus.PUBLISHED, SiteLogStatus.UPDATED])
                )

            with tqdm(
                total=sites.count(),
                desc=_("Validating"),
                unit="sites",
                postfix={"site": ""},
            ) as p_bar:
                for site in sites:
                    p_bar.set_postfix({"site": site.name})
                    for section in Site.sections():
                        head = getattr(site, section.accessor).head()
                        if not hasattr(head, "__iter__"):
                            if head:
                                head = [head]
                            else:
                                head = []
                        for obj in head:
                            if clear:
                                obj._flags = {}
                            try:
                                obj.clean()
                                obj.save()
                            except ValidationError as verr:
                                self.stderr.write(
                                    self.style.ERROR(
                                        _(
                                            "Section {} of site {} has "
                                            "critical error(s): {}"
                                        ).format(
                                            obj.__class__.__name__.lstrip("Site"),
                                            site.name,
                                            str(verr),
                                        )
                                    )
                                )
                                critical += 1
                                # this type of error would normally block the
                                # section from being saved - but we let this
                                # go through here and record the error as a
                                # normal flag
                                for field, errors in verr.error_dict.items():
                                    obj._flags[field] = "\n".join(
                                        err.message for err in errors
                                    )

                    if schema:
                        alert = GeodesyMLInvalid.objects.check_site(site=site)
                        if alert:
                            invalid += 1
                        else:
                            valid += 1

                    # site.update_status(save=True)
                    p_bar.update(n=1)

            Site.objects.synchronize_denormalized_state(skip_form_updates=True)

        if schema:
            if valid:
                self.stdout.write(
                    self.style.SUCCESS(
                        _("{valid} sites had valid GeodesyML documents.").format(
                            valid=valid
                        )
                    )
                )
            if invalid:
                self.stdout.write(
                    self.style.ERROR(
                        _(
                            "{invalid} sites do not have valid GeodesyML documents."
                        ).format(invalid=invalid)
                    )
                )

        new_flags = Site.objects.aggregate(Sum("num_flags"))["num_flags__sum"]

        delta = (new_flags or 0) - (old_flag_count or 0)

        if delta >= 0:
            change = "added"
        else:
            change = "removed"

        self.stdout.write(
            self.style.NOTICE(
                _("{delta} flags were {change}.").format(
                    delta=abs(delta), change=change
                )
            )
        )

        self.stdout.write(
            self.style.NOTICE(
                _(
                    "There are a total of {new_flags} validation flags across "
                    "{site_count} sites. {critical} are critical."
                ).format(
                    new_flags=(new_flags or 0),
                    site_count=sites.count(),
                    critical=critical,
                )
            )
        )
