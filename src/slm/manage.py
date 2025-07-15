#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

from django.core.management import execute_from_command_line


def main():
    """Run administrative tasks."""

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "slm.settings.root")
    # We use a slightly different logger config if we're running a management command vs serving
    if len(sys.argv) > 1:
        subcommand = sys.argv[1]
        if subcommand != "runserver":
            os.environ["SLM_MANAGEMENT_FLAG"] = "ON"
        ##################################################
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
