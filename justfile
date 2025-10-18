set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
set unstable := true
set script-interpreter := ['uv', 'run', '--script']

export PYTHONPATH := source_directory()
export DJANGO_SETTINGS_MODULE := "tests.settings"

[private]
default:
    @just --list --list-submodules

# run Django's manage
[script]
manage *COMMAND:
    import os
    import sys
    import shlex
    from pathlib import Path
    from django.core import management
    management.execute_from_command_line(["just manage", *shlex.split("{{ COMMAND }}")])

# install the uv package manager
[linux]
[macos]
install-uv:
    curl -LsSf https://astral.sh/uv/install.sh | sh

# install the uv package manager
[windows]
install-uv:
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

[linux]
[macos]
install-nvm:
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

[linux]
[macos]
install-node: install-nvm
    source ~/.nvm/nvm.sh && nvm install 22

# install the uv package manager
[windows]
install-nvm:
    winget install Schniz.fnm

[windows]
install-node: install-nvm
    fnm install 22

install-esbuild: install-node
    npm install esbuild

# setup the venv and pre-commit hooks, optionally specify python version
setup python="python":
    uv venv -p {{ python }}
    @just run pre-commit install

# install git pre-commit hooks
install-precommit:
    @just run pre-commit install

# update and install development dependencies
install *OPTS:
    uv sync --all-extras {{ OPTS }}
    @just run pre-commit install

# install without extra dependencies
install-basic:
    uv sync

# install documentation dependencies
install-docs:
    uv sync --group docs --all-extras

[script]
_lock-python:
    import tomlkit
    import sys
    f='pyproject.toml'
    d=tomlkit.parse(open(f).read())
    d['project']['requires-python']='=={}'.format(sys.version.split()[0])
    open(f,'w').write(tomlkit.dumps(d))

# lock to specific python and versions of given dependencies
test-lock +PACKAGES: _lock-python
    uv add {{ PACKAGES }}

# run static type checking
check-types:

#     @just run mypy
#     @just run pyright

# run package checks
check-package:
    @just run pip check

# remove doc build artifacts
[script]
clean-docs:
    import shutil
    shutil.rmtree('./doc/build', ignore_errors=True)

# remove the virtual environment
[script]
clean-env:
    import shutil
    import sys
    shutil.rmtree(".venv", ignore_errors=True)

# remove all git ignored files
clean-git-ignored:
    git clean -fdX

# remove all non repository artifacts
clean: clean-docs clean-git-ignored clean-env

# build html documentation
build-docs-html: install-docs
    @just run sphinx-build --fresh-env --builder html --doctree-dir ./doc/build/doctrees ./doc/source ./doc/build/html

[script]
_open-pdf-docs:
    import webbrowser
    from pathlib import Path
    webbrowser.open(f"file://{Path('./doc/build/pdf/slm.pdf').absolute()}")

# build pdf documentation
build-docs-pdf: install-docs
    @just run sphinx-build --fresh-env --builder latex --doctree-dir ./doc/build/doctrees ./doc/source ./doc/build/pdf
    make -C ./doc/build/pdf
    @just _open-pdf-docs

# build the docs
build-docs: build-docs-html

# build src package and wheel
build:
    uv build

# open the html documentation
[script]
open-docs:
    import os
    import webbrowser
    webbrowser.open(f'file://{os.getcwd()}/doc/build/html/index.html')

# build and open the documentation
docs: build-docs-html open-docs

# serve the documentation, with auto-reload
docs-live: install-docs
    @just run sphinx-autobuild doc/source doc/build --open-browser --watch src --port 8001 --delay 1

_link_check:
    -uv run sphinx-build -b linkcheck -Q -D linkcheck_timeout=10 ./doc/source ./doc/build

_spell_check:
    -uv run sphinx-build -b spelling -Q ./doc/source ./doc/build/spelling

# check the documentation links for broken links
[script]
check-docs-links: _link_check
    import os
    import sys
    import json
    from pathlib import Path
    # The json output isn't valid, so we have to fix it before we can process.
    data = json.loads(f"[{','.join((Path(os.getcwd()) / 'doc/build/output.json').read_text().splitlines())}]")
    broken_links = [link for link in data if link["status"] not in {"working", "redirected", "unchecked", "ignored"}]
    if broken_links:
        for link in broken_links:
            print(f"[{link['status']}] {link['filename']}:{link['lineno']} -> {link['uri']}", file=sys.stderr)
        sys.exit(1)

# lint the documentation
check-docs:
    @just run doc8 --ignore-path ./doc/build --max-line-length 100 -q ./doc

# check the documentation for misspelled words
[script]
check-docs-spelling: _spell_check
    import os
    import sys
    import json
    import re
    from pathlib import Path
    from rich.console import Console
    from rich.text import Text

    error_rex = re.compile(r"^(.*?):(\d+): \((.*?)\) \[(.*?)\]$") 
    spelling_dir = Path(os.getcwd()) / 'doc/build/spelling'

    for file in spelling_dir.glob("*.spelling"):
        with file.open() as f:
            for misspelling in f:
                if misspelling.strip():
                    mtch = error_rex.match(misspelling.strip())
                    if mtch:
                        filepath, lineno, word, suggestions = mtch.groups()
                        suggestions_list = [s.strip().strip('"') for s in suggestions.split(",")]
                        console = Console()
                        output = Text()
                        output.append(filepath, style="blue")
                        output.append(f":{lineno}", style="yellow")
                        output.append(f": ", style="default")
                        output.append(word, style="red")
                        output.append(" → ", style="default")
                        output.append(", ".join(suggestions_list), style="green")
                        console.print(output)
        sys.exit(1)

# lint the code
check-lint:
    @just run ruff check --select I
    @just run ruff check

# check if the code needs formatting
check-format:
    @just run ruff format --check

# check that the readme renders
check-readme:
    @just run python -m readme_renderer ./README.md -o /tmp/README.html

# sort the python imports
sort-imports:
    @just run ruff check --fix --select I

# format the code and sort imports
format: sort-imports
    just --fmt --unstable
    @just run ruff format

# sort the imports and fix linting issues
lint: sort-imports
    @just run ruff check --fix

# fix formatting, linting issues and import sorting
fix: lint format

# run all static checks
check: check-lint check-format check-types check-package check-docs check-docs-links check-readme

# run all tests
test-all *ENV: coverage-erase
    uv run {{ ENV }} --all-extras --exact pytest --cov-append

# run tests
test *TESTS:
    @just run pytest --cov-append {{ TESTS }}

# run the pre-commit checks
precommit:
    @just run pre-commit

# erase any coverage data
coverage-erase:
    @just run coverage erase

# generate the test coverage report
coverage:
    @just run coverage combine --keep *.coverage
    @just run coverage report
    @just run coverage xml

# run the command in the virtual environment
run +ARGS:
    uv run {{ ARGS }}

# fetch the intersphinx references for the given package
[script]
fetch-refs LIB: install-docs
    import os
    from pathlib import Path
    import logging as _logging
    import sys
    import runpy
    from sphinx.ext.intersphinx import inspect_main
    _logging.basicConfig()

    libs = runpy.run_path(Path(os.getcwd()) / "doc/source/conf.py").get("intersphinx_mapping")
    url = libs.get("{{ LIB }}", None)
    if not url:
        sys.exit(f"Unrecognized {{ LIB }}, must be one of: {', '.join(libs.keys())}")
    if url[1] is None:
        url = f"{url[0].rstrip('/')}/objects.inv"
    else:
        url = url[1]

    raise SystemExit(inspect_main([url]))

# validate the given version string against the lib version
[script]
validate_version VERSION:
    import re
    import tomllib
    import slm
    from packaging.version import Version
    raw_version = "{{ VERSION }}".lstrip("v")
    version_obj = Version(raw_version)
    # the version should be normalized
    assert str(version_obj) == raw_version, f"{version_obj} != {raw_version}"
    # make sure all places the version appears agree
    pyproject_v = tomllib.load(open('pyproject.toml', 'rb'))['project']['version']
    assert raw_version == pyproject_v, f"{raw_version} != {pyproject_v}"
    assert raw_version == slm.__version__, f"{raw_version} != {slm.__version__}"
    print(raw_version)

# issue a relase for the given semver string (e.g. 2.1.0)
release VERSION:
    @just validate_version v{{ VERSION }}
    git tag -s v{{ VERSION }} -m "{{ VERSION }} Release"
    git push origin v{{ VERSION }}
