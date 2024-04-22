"""
Update the data availability information for each station.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import CommandError
from django.utils.translation import gettext_lazy as _
from django_typer import TyperCommand


class Command(TyperCommand):
    help = _(
        "Set the Django Site database object to reflect SLM_SITE_NAME and "
        "SLM_ORG_NAME in settings."
    )

    suppressed_base_arguments = {
        *TyperCommand.suppressed_base_arguments,
        "version",
        "pythonpath",
        "settings",
        "skip-checks",
    }
    requires_migrations_checks = False
    requires_system_checks = []

    def handle(self):
        domain = getattr(settings, "SLM_SITE_NAME", None)
        org = getattr(settings, "SLM_ORG_NAME", None)
        if domain and org:
            site = Site.objects.get_current()
            site.domain = domain
            site.name = org
            site.save()
        else:
            raise CommandError(
                "To set the default Site object, both SLM_SITE_NAME and "
                "SLM_ORG_NAME must be defined in settings."
            )
