import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import django
from django.conf import settings
from django_typer.completers import complete_path
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

1. Create a database called `{site}`.

2. Use `poetry` to install your project's virtual environment:

    {install_poetry}

    Install dependencies:

    ```bash
    poetry install
    ```

3. To install your database and import existing sitelogs, run:
    
    ```bash
    {site} routine install
    ```

4. To run the development server, run:
    
    ```bash
    network runserver
    ```
"""

INSTALL_POETRY = """
    **You do not have `poetry` installed, see**: https://python-poetry.org/docs/#installing-with-the-official-installer
"""


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
    ] = "",
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
    include_map: Annotated[
        bool,
        Option(
            "--include-map",
            prompt="Install the mapbox map app?",
            help="Install the mapbox map app?",
        ),
    ] = False,
    use_igs_validation: Annotated[
        bool,
        Option(
            "--use-igs-validation",
            prompt="Use IGS sitelog validation defaults?",
            help="Use IGS sitelog validation defaults?",
        ),
    ] = False,
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
    if not organization:
        organization = domain.title()
    org = organization.replace(" ", "_").lower()
    extension_app = extension_app.format(org=(org or "slm"))
    site = site.format(subdomain=subdomain).replace(" ", "_").lower()
    project_dir = project_dir.format(subdomain=subdomain)
    package_name = package_name.format(project_dir=project_dir)

    # find site packages dir
    local_slm = None
    slm_pth = Path(slm.__file__).parent
    for pth in (Path(pth) for pth in sys.path):
        if pth.name == "site-packages":
            if pth not in slm_pth.parents:
                if yes(
                    input(
                        "It looks like you are using a local clone of the SLM, would "
                        "you prefer to use this instead of a release on pypi? (Y/n): "
                    )
                ):
                    local_slm = os.path.relpath(
                        slm_pth.parent, directory.absolute().resolve() / project_dir
                    )
                break

    ctx = {
        "netloc": netloc,
        "subdomain": subdomain,
        "organization": organization,
        "org": org,
        "project_dir": project_dir,
        "site": site,
        "production_dir": production_dir.format(site=site),
        "slm_version": slm.__version__,
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
        exclude=[template_dir / "{{ project_dir }}/{{ extension_app }}/templates"],
    )
    engine.render_to_disk(
        "{{ project_dir }}/{{ extension_app }}/templates/**",
        context=ctx,
        dest=directory,
        render_contents=False,
    )

    output = (directory / project_dir).absolute().resolve()
    assert output.is_dir() and output.exists()

    Console().print(
        Markdown(
            REPORT_MARKDOWN.format(
                output=output,
                develop=(output / "sites" / site / "develop/__init__.py").relative_to(
                    output
                ),
                production=(
                    output / "sites" / site / "production/__init__.py"
                ).relative_to(output),
                site=site,
                install_poetry=INSTALL_POETRY if not shutil.which("poetry") else "",
                pyproject=(output / "pyproject.toml").relative_to(output),
            )
        )
    )


if __name__ == "__main__":
    app()
