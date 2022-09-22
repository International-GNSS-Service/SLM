# SLM
SiteLog Manager

This repository houses the code base that powers the SLM website 
https://slm.igs.org.

## Table of Contents
1. [Design](#Design)
   1. [Stack](#Stack)
   2. [Organization](#Organization)
2. [DevOps](#DevOps)
   1. [Local Development](#Local-Development)
      1. [Environment & Setup](#Environment--Setup)
   3. [Dependency Management](#Dependency-Management)

## Design

SLM is built in Python using the [Django website development framework.](https://www.djangoproject.com/)
Django is well documented. A basic understanding of how it works is helpful to understand how SLM is
put together. In addition to the [good intro tutorials](https://docs.djangoproject.com/en/stable/intro/tutorial01/), it's
helpful to understand [how reusable Django apps work](https://docs.djangoproject.com/en/stable/intro/reusable-apps/), how
[settings files work](https://docs.djangoproject.com/en/stable/topics/settings/) and how 
[management commands work.](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/)

### Stack
 
Django can be served behind many http servers. The current production environment uses [Apache](https://httpd.apache.org/)
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
   local Python installations and keep environments clean.
2. [Poetry](https://Python-poetry.org/) is used for dependency and package management.
3. SLM can be configured to use the following relational database management systems (RDBMS). PostgresSQL is preferred.
   
   | RDBMS                                        | Minimum Version   | Management Utilities                                        |
   | ---------------------------------------------| ----------------- | ------------------------------------------------------------|
   | [PostgreSQL](https://www.postgresql.org/)    | 9.6               | [PgAdmin](https://www.pgadmin.org/)                         |
   | [MySQL](https://www.mysql.com/)              | 5.7               | [MySQL Workbench](https://www.mysql.com/products/workbench/)|
   | [MariaDB](https://mariadb.org/)              | 10.2.7            |                                                             |
