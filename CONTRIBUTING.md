# Contributing

Contributions are encouraged! Please use the issue page to submit feature
requests or bug reports. Issues with attached PRs will be given priority and
have a much higher likelihood of acceptance. Please also open an issue and
associate it with any submitted PRs.

## Installation

`slm` uses [Poetry](https://python-poetry.org) for environment, package and 
dependency management:

```console
    poetry install
```

## Documentation

`slm` documentation is generated using 
[Sphinx](https://www.sphinx-doc.org/en/master) with the 
[readthedocs](https://readthedocs.org) theme. Any new feature PRs must provide
updated documentation for the features added. To build the docs run:

```console
    cd ./doc
    poetry run make html
```


## Static Analysis

`slm` uses [Pylint](https://www.pylint.org/) for linting. Header imports are
also standardized  using [isort](https://pycqa.github.io/isort). Before any
PR is accepted the following  must be run, and static  analysis tools should
not produce any errors or warnings. Disabling certain  errors or warnings where
justified is acceptable:

```console
    poetry run isort slm
    poetry run pylint slm
    poetry run doc8 -q doc
    poetry check
    poetry run pip check
    poetry run safety check --full-report
    poetry run python -m readme_renderer ./README.rst
```

## Running Tests

`slm` is setup to use [pytest](https://docs.pytest.org/en/stable) to run unit
tests. All the tests are housed in slm/tests/tests.py. Before a PR is accepted,
all tests must be passing.

To run the full suite:

```console
    poetry run pytest
```

To run a single test, or group of tests in a class:

```console
    poetry run pytest <path_to_tests_file>::ClassName::FunctionName
```

For instance to run all tests in TestDjangoEnums, and then just the
test_properties_and_symmetry test you would do:

```console
    poetry run pytest slm/tests/tests.py::TestSiteLogParsing
    poetry run pytest slm/tests/tests.py::TestSiteLogParsing::test_legacy
```
