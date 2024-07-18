#!/usr/bin/env python
import os
import sys


def main(default_settings: str):
    """Run administrative tasks."""

    # We use a slightly different logger config if we're running
    #   a management command vs serving
    if len(sys.argv) > 1:
        if sys.argv[1] != "runserver":
            os.environ["SLM_MANAGEMENT_FLAG"] = "ON"
    ##################################################

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main(default_settings="slm.tests.settings")
