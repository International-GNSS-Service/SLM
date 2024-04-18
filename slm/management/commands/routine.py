"""
Run routines. Routines are batched commands that accomplish specific well
defined tasks, mostly for DevOps. Routines are specified in
settings.SLM_ROUTINES and are configured as part of the Django/slm
bootstrapping process.

SLM_ROUTINES = {
    'routine name': {
        'group name':
        [
            routine1,
            routine2,
            ...
            routineN
        ]
    }
}

Group names are not important for the routine command, they serve as a means
for settings files to override groups of commands that are part of a routine.
For instance, settings files lower down the stack could override the "default"
group specified in settings/routines.conf for the deploy routine. Individual
routines are specified as tuples of length 2 or 3:
    (priority, routine, phase (optional))
Routines will be executed in priority order. Routines themselves are a tuple of
size 1 to 4:
(
    command name (if management command) or callable,
    args (optional),
    kwargs(optional),
    trailing callable (optional)
)
Specify help text for a routine in settings.SLM_ROUTINE_<NAME> =
'This routine does stuff...'
"""

import logging

from django.conf import settings
from django.core.management import BaseCommand, call_command


def get_parser():
    """
    This instantiates an argparser parser for this command so sphinx doc can
    autogenerate the docs for it.
    """
    cmd = Command()
    parser = cmd.create_parser("manage.py", "routine")
    return parser


def order_routines(routines):
    routine_list = []
    for group, routines in routines.items():
        routine_list += routines
    return [
        (routine[0], routine[1], routine[2] if len(routine) > 2 else None)
        for routine in sorted(routine_list, key=lambda r: r[0])
    ]


class Command(BaseCommand):
    help = "Run collections of management commands as named routines."

    logger = logging.getLogger(__name__ + ".Command")

    ROUTINES = {
        routine: order_routines(groups)
        for routine, groups in getattr(settings, "SLM_ROUTINES", {}).items()
    }

    ROUTINE_PHASES = {}

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

        routine_parsers = parser.add_subparsers(help="Invoke specific batch routine.")

        routines = getattr(settings, "SLM_ROUTINES", {})
        for routine, groups in routines.items():
            r_parser = routine_parsers.add_parser(
                routine, help=getattr(settings, f"SLM_ROUTINE_{routine.upper()}", "")
            )
            r_parser.set_defaults(routine=routine)
            phases = {}
            for group, commands in groups.items():
                for command in commands:
                    if len(command) > 2:
                        phase = command[2].lower()
                        phases.setdefault(phase, []).append(str(command[1][0]))

            if phases:
                for phase, subroutines in phases.items():
                    self.ROUTINE_PHASES.setdefault(routine, []).append(phase)
                    phase_help = getattr(
                        settings, f"SLM_ROUTINE_{routine.upper()}_{phase.upper()}", ""
                    )
                    if phase_help:
                        phase_help += f'{"" if phase_help.endswith(".") else "."} '
                    phase_help += f"Phase {phase} commands include: {subroutines}."

                    r_parser.add_argument(
                        f"--{phase}",
                        action="store_true",
                        dest=phase,
                        default=False,
                        help=phase_help,
                    )
            else:
                self.ROUTINE_PHASES.setdefault(routine, [])

    def handle(self, *args, **options):
        phases = []
        for phase in self.ROUTINE_PHASES[options["routine"]]:
            if options.get(phase, False):
                phases.append(phase)

        for priority, command, phase in self.ROUTINES.get(options["routine"]):
            if phase and phase not in phases:
                continue
            cmd = command[0]
            argv = command[1] if len(command) > 1 else []
            kwargv = command[2] if len(command) > 2 else {}
            trailer = command[3] if len(command) > 3 else lambda: None
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n\n{cmd}({",".join(argv)}{"," if argv else ""}'
                    f'{",".join([var + "=" + str(val) for var, val in kwargv.items()])})'
                )
            )
            if isinstance(cmd, str):
                call_command(cmd, *argv, **kwargv)
            elif callable(cmd):
                cmd(*argv, **kwargv)
            trailer()
