#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""

    # We use a slightly different logger config if we're running
    #   a management command vs serving
    if len(sys.argv) > 1:
        subcommand = sys.argv[1]
        if subcommand != 'runserver':
            os.environ['SLM_MANAGEMENT_FLAG'] = 'ON'
    ##################################################

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
