"""
We update our SLMVersion tag when migrate is run - which should happen everytime the
SLM software is updated.
"""

from django.db import ProgrammingError
from django.db.models.signals import post_migrate, pre_migrate
from django.dispatch import receiver

from slm.models import SLMVersion


@receiver(pre_migrate)
def check_safe_upgrade(**_):
    from slm.management.commands.check_upgrade import Command as CheckUpgrade

    CheckUpgrade().is_safe()


@receiver(post_migrate)
def update_slm_version(**_):
    try:
        SLMVersion.update()
    except ProgrammingError:
        pass
