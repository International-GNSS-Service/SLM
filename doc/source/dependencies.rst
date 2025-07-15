.. include:: refs.rst


.. _dependencies:

============
Dependencies
============

The SLM relies on the following third party packages. We carefully review each third party
dependency for inclusion based on maturity, maintenance activity, security posture and
license compatibility. We also `monitor security vulnerability reports
<https://github.com/International-GNSS-Service/SLM?tab=security-ov-file>`_


Versions
========

When possible we specify wide version ranges on our dependencies. We recognize that downstream users
of the SLM may extend it significantly and we maintain these wide ranges to minimize dependency
version conflicts. We test using both minimum and maximum dependency version resolution.

.. note::

    The SLM will always track :term:`Django LTS releases <Long-term support release>`.
    These are the x.2.x series. This means the SLM will not support more than one Django_
    feature release and that release will always be a x.2.x series.


Runtime Dependencies
====================

**We do not list incidental or development dependencies here. (e.g. dependencies of dependencies
and so on).**

.. list-table:: Direct Python Runtime Dependencies
   :header-rows: 1
   :widths: 25 55 20

   * - Package
     - Usage
     - License
   * - :pypi:`chardet`
     - Determine encoding of text files.
     - `LGPL <https://github.com/chardet/chardet/blob/main/LICENSE>`__
   * - :pypi:`crispy-bootstrap5`
     - Use Bootstrap5 theme for :pypi:`django-crispy-forms`.
     - `MIT <https://github.com/django-crispy-forms/crispy-bootstrap5/blob/main/LICENSE>`__
   * - :pypi:`django`
     - Web framework that forms the foundation of the SLM.
     - `BSD <https://github.com/django/django/blob/main/LICENSE>`__
   * - :pypi:`django-allauth`
     - General purpose authentication framework, includes social auth integrations.
     - `MIT <https://github.com/pennersr/django-allauth/blob/main/LICENSE>`__
   * - :pypi:`django-ckeditor`
     - Browser based rich text editing for emails and about/help pages.
     - `BSD <https://github.com/django-ckeditor/django-ckeditor/blob/main/LICENSE>`__
   * - :pypi:`django-compressor`
     - Build and minify javascript and css artifacts.
     - `MIT <https://github.com/django-compressor/django-compressor/blob/develop/LICENSE>`__
   * - :pypi:`django-crispy-forms`
     - More user friendly form definitions.
     - `MIT <https://github.com/django-crispy-forms/django-crispy-forms/blob/main/LICENSE.txt>`__
   * - :pypi:`django-enum`
     - Use Python :class:`~enum.Enum` types as model fields.
     - `MIT <https://github.com/django-commons/django-enum/blob/main/LICENSE>`__
   * - :pypi:`django-environ`
     - Configure settings from environment variables.
     - `MIT <https://github.com/joke2k/django-environ/blob/main/LICENSE.txt>`__
   * - :pypi:`django-filter`
     - Build URL query filters for the API.
     - `BSD <https://github.com/carltongibson/django-filter/blob/main/LICENSE>`__
   * - :pypi:`django-ipware`
     - Get client IP address from a Django_ request.
     - `MIT <https://github.com/un33k/django-ipware/blob/master/LICENSE>`__
   * - :pypi:`django-polymorphic`
     - Define polymorphic models for Django_.
     - `BSD <https://github.com/jazzband/django-polymorphic/blob/master/LICENSE>`__
   * - :pypi:`django-render-static`
     - Render static files at deployment time. Transpilation of Python code to Javascript.
     - `MIT <https://github.com/bckohan/django-render-static/blob/main/LICENSE>`__
   * - :pypi:`django-routines`
     - Define collections of commands as runnable routines in settings.
     - `MIT <https://github.com/bckohan/django-routines/blob/main/LICENSE>`__
   * - :pypi:`django-split-settings`
     - Compose settings from multiple python files.
     - `BSD <https://github.com/wemake-services/django-split-settings/blob/master/LICENSE>`__
   * - :pypi:`django-typer`
     - Build Django_ management commands using Typer_.
     - `MIT <https://github.com/django-commons/django-typer/blob/main/LICENSE>`__
   * - :pypi:`django-widget-tweaks`
     - Easy customization of html elements in template code.
     - `MIT <https://github.com/jazzband/django-widget-tweaks/blob/master/LICENSE>`__
   * - :pypi:`djangorestframework`
     - Build RESTful APIs.
     - `BSD <https://github.com/encode/django-rest-framework/blob/master/LICENSE.md>`__
   * - :pypi:`djangorestframework-gis`
     - Allow API endpoints to render GIS model field types (polygons).
     - `MIT <https://github.com/openwisp/django-rest-framework-gis/blob/master/LICENSE>`__
   * - :pypi:`enum-properties`
     - Define :class:`~enum.Enum` types with additional properties.
     - `MIT <https://github.com/bckohan/enum-properties/blob/main/LICENSE>`__
   * - :pypi:`geojson`
     - Python bindings and utilities for GeoJSON_.
     - `BSD <https://github.com/jazzband/geojson/blob/main/LICENSE.rst>`__
   * - :pypi:`importlib-resources`
     - Access data files within packages.
     - Apache 2.0
   * - :pypi:`Jinja2`
     - Render site log files in GeodesyML and legacy ASCII formats.
     - `BSD <https://github.com/pallets/jinja/blob/main/LICENSE.txt>`__
   * - :pypi:`lxml`
     - Parse GeodesyML_ files.
     - `BSD <https://github.com/lxml/lxml/blob/master/LICENSE.txt>`__
   * - :pypi:`packaging`
     - Parse python package version strings.
     - `BSD/Apache 2.0 <https://github.com/pypa/packaging/blob/main/LICENSE>`__
   * - :pypi:`Pillow`
     - For image manipulation and meta data extraction.
     - `MIT-CMU <https://github.com/python-pillow/Pillow/blob/main/LICENSE>`__
   * - :pypi:`polyline`
     - Compress polygons into text that can be passed in urls.
     - `MIT <https://github.com/frederickjansen/polyline/blob/master/LICENSE>`__
   * - :pypi:`psycopg`
     - Talk to postgres databases.
     - `LGPL <https://github.com/psycopg/psycopg/blob/master/LICENSE.txt>`__
   * - :pypi:`python-dateutil`
     - Powerful extensions to the standard datetime module.
     - `BSD/Apache 2.0 <https://github.com/dateutil/dateutil/blob/master/LICENSE>`__
   * - :pypi:`requests`
     - Make HTTP requests.
     - `Apache 2.0 <https://github.com/psf/requests/blob/main/LICENSE>`__
   * - :pypi:`rich`
     - Nice formatting for terminal output.
     - `MIT <https://github.com/Textualize/rich/blob/master/LICENSE>`__
   * - :pypi:`tqdm`
     - Terminal progress bars.
     - `MIT/MPLv2 <https://github.com/tqdm/tqdm/blob/master/LICENCE>`__


Development Dependencies
========================

.. todo::

    Dev dependencies

Documentation Dependencies
==========================

.. todo::

    Doc dependencies
