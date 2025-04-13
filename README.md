[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm/)
[![PyPI djversions](https://img.shields.io/pypi/djversions/igs-slm.svg)](https://pypi.org/project/igs-slm/)
[![PyPI status](https://img.shields.io/pypi/status/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm)
[![Documentation Status](https://readthedocs.org/projects/igs-slm/badge/?version=latest)](http://igs-slm.readthedocs.io/?badge=latest/)
[![codecov](https://codecov.io/github/International-GNSS-Service/SLM/graph/badge.svg?token=PQVWN1LNM3)](https://codecov.io/github/International-GNSS-Service/SLM)
[![Test Status](https://github.com/International-GNSS-Service/SLM/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/International-GNSS-Service/SLM/actions/workflows/test.yml?branch=main)
[![Lint Status](https://github.com/International-GNSS-Service/SLM/workflows/lint/badge.svg)](https://github.com/International-GNSS-Service/SLM/actions/workflows/lint.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# ![](https://github.com/International-GNSS-Service/SLM/blob/main/src/slm/static/slm/img/slm-logo.svg?raw=true) 
Site Log Manager (SLM)
The Site Log Manager (SLM) is a web framework for managing [GNSS](https://en.wikipedia.org/wiki/Satellite_navigation) ground station meta data. `SLM` is maintained by the [International GNSS Service](https://igs.org/) and is freely licensed for general use under the [MIT License](https://opensource.org/license/mit). The SLM is implemented in [Python](https://python.org) and JavaScript using the [Django web framework](https://djangoproject.com).

The SLM aims to provide:

   * GNSS Site meta data (site log) management with a moderation workflow.
   * Support for multiple organizations and networks to be managed in an access controlled way.
   * Full legacy site log format support (both import and export).
   * Full GeodesyML support (both import and export).
   * JSON renderings of meta data.
   * Point-and-click graphical editing of site log data.
   * Public RESTful api for searching site log data.
   * Authenticated RESTful api for updating site log data.
   * Full access to the historical record.
   * Visualizations of networks and site information.
   * Configurable data validation that goes above and beyond schema validation.
   * Image and file attachments to sites.
   * A no-fork extensible architecture that allows organizations to modify out-of-the box behavior
     with plugins.

Full documentation is available on [igs-slm.readthedocs.org](https://igs-slm.rtfd.org) and speaks to multiple audiences:

   * **Developers** will want to refer to the [Installation](https://igs-slm.rtfd.org/en/latest/installation.html), [Architecture](https://igs-slm.rtfd.org/en/latest/architecture.html), [Commands](https://igs-slm.rtfd.org/en/latest/commands.html) and [Reference](https://igs-slm.rtfd.org/en/latest/reference.html) sections.
   * **System administrators** may be interested in [operations](https://igs-slm.rtfd.org/en/latest/overview.html) and [Commands](https://igs-slm.rtfd.org/en/latest/operations.html).
   * **Users** and **network coordinators** will be interested in the [User Manual](https://igs-slm.rtfd.org/en/latest/manual.html).
   * **Developers** wishing to work with SLM managed data will be interested in the [APIs](https://igs-slm.rtfd.org/en/latest/APIs.html).
   * **Everyone**, but particularly **program managers** will want to take a look at the
     [Overview](https://igs-slm.rtfd.org/en/latest/overview.html).

> ## ⚠️ **Warning**
> **The SLM has reached beta-maturity but is still undergoing rapid development. Check back soon for new documentation and updates. A version 1.0 stable release is expected in late September 2024.**

Please use the [discussions page](https://github.com/International-GNSS-Service/SLM/discussions/landing) for general inquiry and the [issues page](https://github.com/International-GNSS-Service/SLM/issues) to report bugs. Our road map is on the [projects page](https://github.com/International-GNSS-Service/SLM/projects).
