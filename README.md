[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm/)
[![PyPI djversions](https://img.shields.io/pypi/djversions/igs-slm.svg)](https://pypi.org/project/igs-slm/)
[![PyPI status](https://img.shields.io/pypi/status/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm)
[![Documentation Status](https://readthedocs.org/projects/igs-slm/badge/?version=latest)](http://igs-slm.readthedocs.io/?badge=latest/)
[![codecov](https://codecov.io/github/International-GNSS-Service/SLM/graph/badge.svg?token=PQVWN1LNM3)](https://codecov.io/github/International-GNSS-Service/SLM)
[![Test Status](https://github.com/International-GNSS-Service/SLM/actions/workflows/test.yml/badge.svg?branch=master)](https://github.com/International-GNSS-Service/SLM/actions/workflows/test.yml?branch=master)
[![Lint Status](https://github.com/International-GNSS-Service/SLM/workflows/lint/badge.svg)](https://github.com/International-GNSS-Service/SLM/actions/workflows/lint.yml)
[![Security Status](https://github.com/International-GNSS-Service/SLM/workflows/security/badge.svg)](https://github.com/International-GNSS-Service/SLM/actions/workflows/security.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# ![](https://github.com/International-GNSS-Service/SLM/blob/master/slm/static/slm/img/slm-logo.svg?raw=true) 
Site Log Manager (SLM)

The Site Log Manager (SLM) is a web platform that aims to provide:

1. GNSS Site meta data (site log) management with a moderation workflow.
2. Support for multiple organizations and networks to be managed in an access controlled way.
3. Full legacy site log format support (both import and export).
4. Full GeodesyML support (both import and export).
5. JSON renderings of meta data.
6. Point-and-click graphical editing of site log data.
7. Public RESTful api for searching site log data.
8. Authenticated RESTful api for updating site log data.
9. Full access to the historical record.
10. Visualizations of networks and site information.
11. Configurable data validation that goes above and beyond schema validation.
12. Image and file attachments to sites.    
13. A no-fork extensible architecture that allows organizations to modify out-of-the box
behavior with plugins.

This code base has reached beta-maturity but is still undergoing rapid development. Check back soon 
for new documentation and updates.


## Table of Contents
1. [Design](#Design)
   1. [Stack](#Stack)
   2. [Organization](#Organization)

## Design

SLM is built in Python using the [Django website development framework.](https://www.djangoproject.com/)
Django is well documented. A basic understanding of how it works is helpful to understand how SLM is
put together. In addition to the [good intro tutorials](https://docs.djangoproject.com/en/stable/intro/tutorial01/), it's
helpful to understand [how reusable Django apps work](https://docs.djangoproject.com/en/stable/intro/reusable-apps/), how
[settings files work](https://docs.djangoproject.com/en/stable/topics/settings/) and how 
[management commands work.](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/)

### Stack
 
Django can be served behind many http servers. A common production environment uses [Apache](https://httpd.apache.org/)
managing Django as a [WSGI](https://modwsgi.readthedocs.io/en/develop/index.html) daemon, but
another common setup involves proxying a [gunicorn](https://gunicorn.org/) instance behind [nginx](https://www.nginx.com).
In addition to Django, other critical components of the software stack are listed in the table below. Not all Python
dependencies are listed because many are incidental.

| Dependency                                                                     | Description                                          |
| ------------------------------------------------------------------------------ | ---------------------------------------------------- |
| [PostgreSQL](https://www.postgresql.org/)                                      | Relation database management system                  |
| [Django](https://djangoproject.com)                                            | Website development framework                        |
| [jQuery](https://jquery.com/)                                                  | Javascript DOM navigation library                    |
| [DataTables](https://datatables.net/)                                          | Javascript tables library                            |
| [Bootstrap](https://getbootstrap.com/)                                         | CSS framework                                        |
| [djangorestframework](https://www.django-rest-framework.org/)                  | RESTful API framework for Django                     |
| [django-split-settings](https://github.com/sobolevn/django-split-settings)     | Composite settings files for Django                  |
| [django_compressor](https://django-compressor.readthedocs.io/en/stable/)       | Static file compression and management               |
| [memcached](https://memcached.org/)                                            | Memory object caching system                         |
| [django-render-static](https://django-render-static.readthedocs.io/en/latest/) | Static file rendering, javascript urls               |
| [django-debug-toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/) | Debugging components for Django sites (test only)    |


### Organization

#### Environment & Setup

1. [pyenv](https://github.com/pyenv/pyenv) is not strictly required, but it is highly recommended to help manage multiple
   local Python installations and keep environments clean. Python 3.8+ is required.
2. [Poetry](https://Python-poetry.org/) is used for dependency and package management.
3. SLM requires PostgresSQL along with the PostGIS extension that enables geographic queries to be run directly by the database.
   
   | RDBMS                                        | Minimum Version   | Management Utilities                                        |
   | ---------------------------------------------| ----------------- | ------------------------------------------------------------|
   | [PostgreSQL](https://www.postgresql.org/)    | 12                | [PgAdmin](https://www.pgadmin.org/)                         |
