from django.utils.translation import gettext_lazy as _
from django_routines import command, routine

routine(
    "deploy",
    _(
        "Run collection of commands that likely need to be run whenever code is updated."
    ),
    switch_helps={
        "initial": _(
            "Run collection of commands that should only be run on the first deployment."
        )
    },
)

command("deploy", "check", "--deploy")
command("deploy", "migrate", priority=11)
command("deploy", "renderstatic", priority=20)
command("deploy", "collectstatic", "--no-input", priority=21)
command("deploy", "set_site", priority=22)
command("deploy", "createsuperuser", priority=100)
command("deploy", "synchronize", priority=110)
command("deploy", "shellcompletion", "install", priority=120, switches=["initial"])
