import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import django
import environ
from django.conf import settings
from django_typer.completers import complete_path
from packaging.version import Version
from render_static.engine import StaticTemplateEngine
from rich.console import Console
from rich.markdown import Markdown
from typer import Argument, Option, Typer, secho
from typing_extensions import Annotated

import slm

template_dir = Path(__file__).parent / "templates"

app = Typer()


def yes(response):
    return not response or response.lower() in ["y", "yes", "true", "1"]


REPORT_MARKDOWN = """
## SLM Project Information

**Your project has been written to:** `{output}`

- **Develop settings:** `{develop}`
- **Production settings:** `{production}`
- **Manage Script:** `{site}`
- **Package Config:** `{pyproject}`

### Installation Instructions

1. Create a database called `{database_name}`.

2. Use `uv` to install your project's virtual environment:

    {install_uv}

    Install dependencies:

    ```bash
    uv sync --all-extras
    ```

3. To install your database and import existing sitelogs, run:
    
    ```bash
    uv run {site} routine install
    ```

4. To run the development server, run:
    
    ```bash
    uv run {site} runserver
    ```
"""

INSTALL_UV = """
    **You do not have `uv` installed, see**: https://docs.astral.sh/uv/getting-started/installation/
"""


def sanitize_package_dir(name: str) -> str:
    """
    Convert an arbitrary string to a valid Python importable name.

    Rules:
    - Replace any non-alphanumeric character with underscore.
    - Collapse multiple underscores.
    - Remove leading/trailing underscores.
    - Lowercase the result.
    """
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9]+", "_", name)).strip("_").lower()


def sanitize_package_name(name: str) -> str:
    """
    Replace illegal characters in a package name with underscores
    according to PyPI naming rules (PEP 508).
    """
    return re.sub(
        r"_+", "_", re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip(".-")
    ).lower()


@app.command(
    help="Create a directory structure for an slm deployment. This includes settings files and an extension app. You can change any names or settings at a later time!"
)
def main(
    netloc: Annotated[
        str,
        Argument(
            help="The network location of your production deployment will be hosted on. (e.g. slm.igs.org)",
            show_default=False,
        ),
    ],
    directory: Annotated[Path, Argument(shell_complete=complete_path)] = os.getcwd(),
    organization: Annotated[
        str,
        Option(
            prompt="What is the name of your organization?",
            help="What is the name of your organization?",
        ),
    ] = "{domain}",
    project_dir: Annotated[
        str,
        Option(
            prompt="What should we name your project directory?",
            help="What should we name your project directory?",
        ),
    ] = "{subdomain}",
    package_name: Annotated[
        str,
        Option(
            prompt="What should we name your installable wheel?",
            help="What should we name your installable wheel?",
        ),
    ] = "{project_dir}",
    site: Annotated[
        str,
        Option(
            prompt="What is the name of your site?",
            help="What is the name of your site?",
        ),
    ] = "{subdomain}",
    production_dir: Annotated[
        str,
        Option(
            prompt="Where should files live in production?",
            help="Where should files live in production?",
        ),
    ] = "/var/www/{site}/production",
    extension_app: Annotated[
        str,
        Option(
            prompt="What should we call your custom Django app?",
            help="What should we call your custom Django app?",
        ),
    ] = "{org}_extensions",
    database: Annotated[
        str,
        Option(
            prompt="How should we connect to the database (db url)?",
            help="How should we connect to the database (db url)?",
        ),
    ] = "postgis:///{site}",
    include_map: Annotated[
        bool,
        Option(
            "--no-include-map",
            prompt="Install the mapbox map app?",
            help="Install the mapbox map app?",
        ),
    ] = True,
    use_igs_validation: Annotated[
        bool,
        Option(
            "--no-use-igs-validation",
            prompt="Use IGS sitelog validation defaults?",
            help="Use IGS sitelog validation defaults?",
        ),
    ] = True,
):
    netloc = (urlparse(netloc).netloc or netloc).lower()
    parts = netloc.split(".")
    if len(parts) == 2:
        subdomain = "www"
        domain = parts[0]
    elif len(parts) > 2:
        subdomain = parts[0]
        domain = parts[1]
    else:
        secho(
            "Unable to interpret network location: {netloc}".format(netloc=netloc),
            fg="red",
        )
        sys.exit(1)

    if extension_app == "slm":
        secho(
            'extension_app cannot be "slm" this will clash with the slm namespace.',
            fg="red",
        )
        sys.exit(1)

    if "." in extension_app:
        secho(
            f'extension_app ({extension_app}) cannot have any "." in its name.',
            fg="red",
        )
        sys.exit(1)

    settings.configure(
        INSTALLED_APPS=[],
        DEBUG=False,
        TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates"}],
    )
    django.setup()

    engine = StaticTemplateEngine(
        {
            "ENGINES": [
                {
                    "BACKEND": "render_static.backends.StaticDjangoTemplates",
                    "DIRS": [template_dir],
                    "OPTIONS": {
                        "loaders": ["render_static.loaders.StaticFilesystemBatchLoader"]
                    },
                }
            ]
        }
    )
    if not organization or organization == "{domain}":
        parts = domain.split(".")
        organization = parts[0]
        if len(parts) > 1:
            organization = parts[-2]
        organization = organization.title()
    org = organization.replace(" ", "_").replace(".", "_").lower()
    extension_app = sanitize_package_dir(extension_app.format(org=(org or "slm")))
    site = site.format(subdomain=subdomain).replace(" ", "_").lower()
    project_dir = project_dir.format(subdomain=subdomain)
    package_name = sanitize_package_name(package_name.format(project_dir=project_dir))
    database = database.format(site=site)
    if database.isalpha():
        database = f"postgis:///{database}"

    env = environ.Env()
    database_name = env.db_url_config(
        database, engine="django.contrib.gis.db.backends.postgis"
    )["NAME"]

    if not database_name:
        raise

    # find site packages dir
    local_slm = None
    slm_pth = Path(slm.__file__).parent
    for pth in (Path(pth) for pth in sys.path):
        if pth.name == "site-packages":
            if pth not in slm_pth.parents:
                local_slm = os.path.relpath(
                    slm_pth.parent.parent,
                    directory.absolute().resolve() / project_dir,
                )
                break
            else:
                # uvx --from path edge case
                import json
                from importlib.metadata import version

                direct_url = (
                    pth / f"igs_slm-{version('igs-slm')}.dist-info" / "direct_url.json"
                )
                if direct_url.is_file():
                    installed_from = json.loads(direct_url.read_text()).get("url", None)
                    if installed_from.startswith("file:///"):
                        local_slm = str(Path(installed_from[7:]).resolve())
                        break

    if local_slm:
        if not yes(
            input(
                "It looks like you are using a local clone of the SLM, would "
                "you prefer to use this instead of a release on pypi? (Y/n): "
            )
        ):
            local_slm = None

    ctx = {
        "netloc": netloc,
        "subdomain": subdomain,
        "organization": organization,
        "org": org,
        "project_dir": project_dir,
        "site": site,
        "database": database,
        "database_name": database_name,
        "production_dir": production_dir.format(site=site),
        "slm_version": slm.__version__,
        "slm_version_next_major": f"{Version(slm.__version__).major + 1}.0",
        "extension_app_class": extension_app.title().replace(" ", "").replace("_", ""),
        "extension_app": extension_app.replace(" ", "_").lower(),
        "include_map": include_map,
        "use_igs_validation": use_igs_validation,
        "package_name": package_name.replace("_", "-").replace(" ", "-"),
        "local_slm": local_slm,
    }
    engine.render_to_disk(
        "{{ project_dir }}/**",
        context=ctx,
        dest=directory,
        exclude=[template_dir / "{{ project_dir }}/src/{{ extension_app }}/templates"],
    )
    engine.render_to_disk(
        "{{ project_dir }}/src/{{ extension_app }}/templates/**",
        context=ctx,
        dest=directory,
        render_contents=False,
    )

    output = (directory / project_dir).absolute().resolve()
    assert output.is_dir() and output.exists(), (
        f"Failed to create project directory: {output}"
    )

    Console().print(
        Markdown(
            REPORT_MARKDOWN.format(
                output=output,
                develop=(output / "sites" / site / "develop/__init__.py").relative_to(
                    output
                ),
                database_name=database_name,
                production=(
                    output / "sites" / site / "production/__init__.py"
                ).relative_to(output),
                site=site,
                install_uv=INSTALL_UV if not shutil.which("uv") else "",
                pyproject=(output / "pyproject.toml").relative_to(output),
            )
        )
    )


if __name__ == "__main__":
    app()
