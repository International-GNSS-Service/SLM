"""Load SLM in management mode and run management commands."""
import os
import sys


# Use SLM_DEPLOYMENT environment variable to switch between deployments. In
# production you may want to just set this to "production" in your
# administrative user's shell profile
def main(default_settings: str = f"sites.{{ site }}.{os.environ.get('SLM_DEPLOYMENT', 'develop')}"):
    """Run administrative tasks."""

    # SLM configures loggers differently when running management commands so we can
    # distinguish logs on the server that were from requests or admin tasks. This
    # environment variable is used to signal that the SLM runtime is in management
    # mode.
    if len(sys.argv) > 1 and sys.argv[1] != "runserver":
        os.environ['SLM_MANAGEMENT_FLAG'] = 'ON'

    # Django bootstraps off the settings file defined in this import path.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', default_settings)

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
    main()
