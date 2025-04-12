# Contributing

Contributions are encouraged! Please use the issue page to submit feature requests or bug reports. Issues with attached PRs will be given priority and have a much higher likelihood of acceptance. Please also open an issue and associate it with any submitted PRs.

## Installation

### Install Just

We provide a platform independent justfile with recipes for all the development tasks. You should [install just](https://just.systems/man/en/installation.html) if it is not on your system already. We also install pre-commit hooks that require just to run.

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

To run the full suite:

```bash
just test-all
```

To run a single test, or group of tests in a class:

```bash
just test <path_to_tests_file>::ClassName::FunctionName
```

For instance to run all tests in TestDjangoEnums, and then just the test_properties_and_symmetry test you would do:

```bash
    poetry run pytest slm/tests/tests.py::TestLegacyParser
    poetry run pytest slm/tests/tests.py::TestLegacyParser::test_AAA200USA
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
    build                    # build src package and wheel
    build-docs               # build the docs
    build-docs-html          # build html documentation
    build-docs-pdf           # build pdf documentation
    check                    # run all static checks
    check-docs               # lint the documentation
    check-docs-links         # check the documentation links for broken links
    check-docs-spelling      # check the documentation for misspelled words
    check-format             # check if the code needs formatting
    check-lint               # lint the code
    check-package            # run package checks
    check-readme             # check that the readme renders
    check-types              # run static type checking
    clean                    # remove all non repository artifacts
    clean-docs               # remove doc build artifacts
    clean-env                # remove the virtual environment
    clean-git-ignored        # remove all git ignored files
    coverage                 # generate the test coverage report
    coverage-erase           # erase any coverage data
    docs                     # build and open the documentation
    docs-live                # serve the documentation, with auto-reload
    fix                      # fix formatting, linting issues and import sorting
    format                   # format the code and sort imports
    install *OPTS            # update and install development dependencies
    install-basic            # install without extra dependencies
    install-docs             # install documentation dependencies
    install-precommit        # install git pre-commit hooks
    install-uv               # install the uv package manager
    lint                     # sort the imports and fix linting issues
    manage *COMMAND          # run Django's manage
    open-docs                # open the html documentation
    precommit                # run the pre-commit checks
    release VERSION          # issue a relase for the given semver string (e.g. 2.1.0)
    run +ARGS                # run the command in the virtual environment
    setup python="python"    # setup the venv and pre-commit hooks, optionally specify python version
    sort-imports             # sort the python imports
    test *TESTS              # run tests
    test-all *ENV            # run all tests
    test-lock +PACKAGES      # lock to specific python and versions of given dependencies
    validate_version VERSION # validate the given version string against the lib version
```
