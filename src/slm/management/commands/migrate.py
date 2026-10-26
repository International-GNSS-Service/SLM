"""
Django's migrate, but refuse to run when the upgrade would traverse a version
waypoint (see :django-admin:`check_upgrade`).

The pre_migrate receiver also performs this check, but migrate loads the
migration graph first. For a database that was not migrated by the waypoint
release, the remade migrations are only partially applied and Django fails with
an unrelated error before the receiver is ever reached.
"""

from django.core.management.commands.migrate import Command as MigrateCommand


class Command(MigrateCommand):
    def handle(self, *args, **options):
        from slm.management.commands.check_upgrade import Command as CheckUpgrade

        CheckUpgrade().is_safe()
        return super().handle(*args, **options)
