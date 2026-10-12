# Contributing

Contributions are encouraged! Please use the issue page to submit feature requests or bug reports. Issues with attached PRs will be given priority and have a much higher likelihood of acceptance. Please also open an issue and associate it with any submitted PRs.

## Installation

### Install Just

We provide a platform independent justfile with recipes for all the development tasks. You should [install just](https://just.systems/man/en/installation.html) if it is not on your system already. We also install [prek](https://prek.j178.dev/) pre-commit hooks that require just to run.

`igs-slm` uses [uv](https://docs.astral.sh/uv) for environment, package, and dependency management. If you do not already have ``uv`` installed, just can install it for you:

```bash
just install-uv
```

``just setup`` will install the necessary  if you do not already have it:

```bash
just setup
```

## Documentation

`igs-slm` documentation is generated using [Sphinx](https://www.sphinx-doc.org) with the [furo](https://github.com/pradyunsg/furo) theme. Any new feature PRs must provide updated documentation for the features added. To build the docs run doc8 to check for formatting issues then run Sphinx:

```bash
just docs  # builds docs
just check-docs  # lint the docs
just check-docs-links  # check for broken links in the docs
```

Run the docs with auto rebuild using:

```bash
just docs-live
```

## Static Analysis

`igs-slm` uses [ruff](https://docs.astral.sh/ruff/) for Python linting, header import standardization and code formatting. [mypy](http://mypy-lang.org/) are used for static type checking. Before any PR is accepted the following must be run, and static analysis tools should not produce any errors or warnings. Disabling certain errors or warnings where justified is acceptable:

To fix formatting and linting problems that are fixable run:

```bash
just fix
```

To run all static analysis without automated fixing you can run:

```bash
just check
```

## Running Tests

`igs-slm` is set up to use [pytest](https://docs.pytest.org) to run unit tests. All the tests are housed in `tests`. Before a PR is accepted, all tests must be passing and the code coverage must be at or above the level on main. A small number of exempted error handling branches are acceptable.

The tests require a PostgreSQL database with the PostGIS extension. Connection parameters are read from the ``POSTGRES_DB``, ``POSTGRES_USER``, ``POSTGRES_PASSWORD``, ``POSTGRES_HOST`` and ``POSTGRES_PORT`` environment variables (see ``tests/settings.py``).

To run the full suite:

```bash
just test-all
```

CI tests all supported Python versions. To run the full suite against a specific Python version (e.g. Python 3.13):

```bash
just test-all -p 3.13
```

The browser tests use [Playwright](https://playwright.dev/python/). To install the browser they need:

```bash
just install-browsers
```

To run a single test, or group of tests in a class:

```bash
just test <path_to_tests_file>::ClassName::FunctionName
```

For instance to run all tests in test_commands.py, and then just the test_validate_db test you would do:

```bash
just test tests/smoke/test_commands.py
just test tests/smoke/test_commands.py::test_validate_db
```

To drop into the debugger at the start of a test:

```bash
just debug-test tests/smoke/test_commands.py::test_validate_db
```

## Versioning

``igs-slm`` adheres to [semantic versioning](https://semver.org).

## Issuing Releases

The release workflow is triggered by tag creation. You must have [git tag signing enabled](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits). The justfile has a release shortcut:

```bash
    just release x.x.x
```

## Just Recipes
```shell
just
```

```
Available recipes:
    bandit                       # run bandit static security analysis
    build                        # build docs and package
    build-docs                   # build the docs
    build-docs-html              # build html documentation
    build-docs-pdf               # build pdf documentation
    check *ENV                   # run all static checks
    check-all *ENV               # run all checks including documentation link checking (slow)
    check-docs *ENV              # lint the documentation
    check-docs-links             # check documentation links for broken links
    check-docs-spelling          # check the documentation for misspelled words
    check-format *ENV            # check if the code needs formatting
    check-lint *ENV              # lint the code
    check-package                # run package checks
    check-readme *ENV            # check that the readme renders
    check-types *ENV             # run all static type checking
    check-types-isolated *ENV    # run all static type checking in an isolated environment
    check-types-mypy *ENV        # run static type checking with mypy
    check-types-pyright *ENV     # run static type checking with pyright
    clean                        # remove all non-repository artifacts
    clean-docs                   # remove doc build artifacts
    clean-env                    # remove the virtual environment
    clean-git-ignored            # remove all git ignored files
    coverage                     # generate the test coverage report
    coverage-erase               # erase any coverage data
    debug-test *TESTS            # debug a test
    docs                         # build and open the documentation
    docs-live                    # serve the documentation with auto-reload
    fetch-refs LIB               # fetch intersphinx references for the given package
    fix *ENV                     # fix formatting, linting issues and import sorting
    format *ENV                  # format the code and sort imports
    format-workflows             # format the github workflow files
    install *OPTS="--all-extras" # update and install development dependencies
    install-browsers *ENV        # install the browser used by the Playwright (e2e) tests
    install-prek                 # install git pre-commit hooks
    install-uv                   # install the uv package manager
    lint *ENV                    # sort imports and fix linting issues
    manage *COMMAND              # run Django's manage
    open-docs                    # open the html documentation
    prek                         # run the pre-commit checks
    release VERSION              # issue a release for the given semver string (e.g. 2.1.0)
    run +ARGS                    # run the command in the virtual environment
    setup python="python"        # setup the venv and pre-commit hooks, optionally specify python version
    sort-imports *ENV            # sort the python imports
    test *TESTS                  # run specific tests (project venv)
    test-all *ENV                # run all tests (pass -p for a specific python version, e.g. -p 3.13)
    validate_version VERSION     # validate the given version string against the lib version
    zizmor                       # run zizmor security analysis of CI
```
