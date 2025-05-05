from django.utils.translation import gettext_lazy as _
from django_routines import command, routine

from slm.settings import get_setting

routine(
    "deploy",
    _(
        "Run collection of commands that likely need to be run whenever code is updated."
    ),
    switch_helps={
        "initial": _(
            "Run collection of commands that should only be run on the first deployment."
        ),
        "validate": _("Run validation routines on the entire database."),
    },
)

routine(
    "import",
    _("Import equipment from the IGS and site log data from your own archive."),
)

routine(
    "install",
    _("Install a fresh deployment of the SLM and import data from external sources."),
)

command("deploy", "check", "--deploy")
command("deploy", "shellcompletion", "install", switches=["initial"])
command("deploy", "migrate", priority=11)
command("deploy", "renderstatic", priority=20)
command("deploy", "collectstatic", "--no-input", priority=21)
if get_setting("COMPRESS_OFFLINE", False) and get_setting("COMPRESS_ENABLED", False):
    command("deploy", "compress", priority=22)
command("deploy", "set_site", priority=23)
command("deploy", "validate_db", "--schema", priority=30, switches=["re-validate"])
command("deploy", "synchronize", priority=32, switches=["re-validate"])

command("import", "import_equipment", "antennas", "radomes", "receivers", priority=10)
command("import", "import_archive", priority=20)
command("import", "validate_db", "--schema", priority=30)

command("install", "routine", "deploy", "--initial", priority=0)
command("install", "createsuperuser", priority=10)
command("install", "routine", "import", priority=20)
