"""
The `Django Sites framework <https://docs.djangoproject.com/en/stable/ref/contrib/sites/>`_
is used by the SLM and SLM extensions to store information about the organization name and
domain name being served by the current instance. This command populates that information
from SLM specific settings:

    * SLM_SITE_NAME
    * SLM_ORG_NAME

.. note::

    The sites framework is typically used to support serving multiple domains off the same
    software stack. In our experience it is usually preferable to serve separate domains
    off customized software stacks because their requirements may differ substantially.
    For example network.igs.org and slm.igs.org are both instances of the SLM with
    different configurations.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import CommandError
from django.utils.translation import gettext as _
from django_typer.management import TyperCommand


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
                _(
                    "To set the default Site object, both SLM_SITE_NAME and "
                    "SLM_ORG_NAME must be defined in settings."
                )
            )
