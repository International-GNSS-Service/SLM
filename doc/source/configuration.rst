.. include:: refs.rst

.. _configuration:

=============
Configuration
=============

SLM is built on Django_ which means all of the :doc:`configuration directives<django:ref/settings>`
available on Django_ and on the :ref:`application stack <dependencies>` that comprise SLM are
available. SLM provides additional directives :ref:`referenced here <settings>` to customize its
behavior and operational configuration.

Django_ configuration directives are defined in a settings file which is just a normal python file.
You should first familiarize yourself with how
:doc:`Django configuration works <django:topics/settings>`. The configuration directives in a
settings file are python variables of any type named in all caps. The python import path to this
configuration file must appear in the :envvar:`DJANGO_SETTINGS_MODULE` environment variable.
After Django_ is bootstrapped you can access a configuration directive like so:

.. code-block:: python

    from django.conf import settings

    settings.DIRECTIVE_NAME


One of the most important things to understand about configuring the SLM is that there are two main
semantic flavors of configuration directive:

1. Directives that **configure the operational environment**. For example:
    * where to find the database
    * debugging toggles
    * security toggles

2. Directives that **customize functionality**. For example:
    * password requirements
    * sitelog field validation routines
    * station naming conventions
    * installed Django_ applications

The amount of customization you need to do to the SLM will inform how you configure and deploy your
instance. For simple installations that make no behavioral customizations and that
do not install any additional packages you most likely will not have to write any settings files
and configuring the SLM via :ref:`environment variables <environment_settings>` will be sufficient.
Otherwise you will need to familiarize yourself with how the
:ref:`SLM builds its settings file <building_settings>`.

Simple Environment Settings
===========================

By default the SLM will load environment variables from a file if it can find one. It will
look, in order, for a file at:

1. The file path in the ``SLM_ENV`` environment variable (or settings variable) if it exists.
2. The file located at ``django.conf.settings.BASE_DIR`` / ".env" if it exists.

**Environment variables in the process environment have higher precedence than those defined in
files.**

For example a minimal set of settings to instantiate a functional SLM might look like:

.. code-block:: bash

    DJANGO_SETTINGS_MODULE="slm.settings.root"

.. tip::

    :envvar:`DJANGO_SETTINGS_MODULE` will always need to be defined in the process environment because
    it is required before the environment file load is attempted.

.. code-block:: bash

    # this could be defined in your process env or in BASE_DIR / .env
    BASE_DIR="/var/www/sites/slm/production"
    ADMINS="You <you@yourcompany.com>"
    SLM_SITE_NAME="slm.yourcompany.com"
    SLM_ORG_NAME="Your Company"



.. _building_settings:

Building Settings Files
=======================

Django_ does not enforce any particular configuration design pattern, but the SLM does.
We use two third party extensions:

* :doc:`django-split-settings <django-split-settings:index>` to compose settings from multiple
  files. There are a lot of settings directives and this allows us to namespace like with
  like directives.
* :doc:`django-environ <django-environ:index>` to allow environment variables to override
  select operational directives.

If you need to customize SLM behavior and build more complex settings directives, we highly
recommend using :ref:`slm-startproject <slm-startproject>` to scaffold out your project
and its settings files. Even if you do not ultimately use our recommended configuration, seeing how
we lay out an SLM project may be of some help.

We use :func:`split_settings.tools.include` instead of
:doc:`the import system <python:reference/import>` to combine settings files. There are additional
tools that make splitting settings files up more easy in :mod:`slm.settings`. Once you've defined
your base settings file, that is the file that will be set in :envvar:`DJANGO_SETTINGS_MODULE`, you
will need to import the SLM's root settings file. A notional settings file might look like this:

.. code-block:: python

    from pathlib import Path
    from split_settings.tools import include
    from slm.settings import resource

    # A few settings must be defined before including root
    # These may be defined here or in the environment or environment files
    BASE_DIR = Path("/var/www/path/to/your/site/directory")
    SLM_SITE_NAME = "slm.yourdomain.org"
    SLM_ORG_NAME = "Your Organization"

    # Settings defined above (before inclusion of root) may be overridden
    # by environment variables if they support being read from the environment

    # include SLM default settings. Any setting defined before this
    # will take precedence over the defaults defined by the SLM
    include(resource("slm.settings", "root.py"))

    # Settings defined here or later have the highest precedence

    # After root is included you may read or override defaults, or
    # make adjustments, like adding to or removing parts of complex settings
    # For example, to add another app to the stack:
    INSTALLED_APPS = [
        "your_app",
        *get_setting("INSTALLED_APPS"),
    ]

    # or add another database:
    DATABASES = {
        **get_setting("DATABASES"),
        "my_db": ...
    }

Override Precedence
-------------------

Setting definitions will have the following override precedence:

1. Defined in settings files after inclusion of ``slm.settings.root``.
2. Defined in the process environment (for :ref:`environment_settings`).
3. Defined in environment files (for :ref:`environment_settings`).
4. Defined in settings files before inclusion of ``slm.settings.root``.
5. Default settings defined in ``slm.settings.root``.

.. _environment_settings:

Environment Settings ⚙️
=======================

The following settings may be overridden by environment variables:

.. list-table:: Django Settings Overview
   :header-rows: 1
   :widths: 20 15 45

   * - Setting
     - Type
     - Example
   * - :setting:`BASE_DIR` 🚨
     - :ref:`env_types_path`
     - ``/absolute/path/to/working/dir``
   * - :setting:`SLM_ENV`
     - :ref:`env_types_path`
     - ``/path/to/.env``
   * - :setting:`DEBUG`
     - :ref:`env_types_bool`
     - ``on|off``
   * - :setting:`ALLOWED_HOSTS`
     - :ref:`env_types_list`
     - ``example.com,localhost``
   * - :setting:`ADMINS`
     - :ref:`env_types_list`
     - ``"Display Name <name@email.com>, only@email.com"``
   * - :setting:`GDAL_LIBRARY_PATH`
     - :ref:`env_types_path`
     - ``/usr/lib/x86_64-linux-gnu/libgdal.so``
   * - :setting:`GEOS_LIBRARY_PATH`
     - :ref:`env_types_path`
     - ``/usr/lib/x86_64-linux-gnu/libgeos_c.so``
   * - :setting:`EMAIL_SSL_CERTFILE`
     - :ref:`env_types_path`
     - ``/path/to/smtp/cert``
   * - :setting:`EMAIL_SSL_KEYFILE`
     - :ref:`env_types_path`
     - ``/path/to/smtp/key``
   * - :setting:`SLM_CACHE`
     - :ref:`cache url <environ-env-cache-url>`
     - ``memcache://127.0.0.1:11211``
   * - :setting:`SLM_DATABASE`
     - :ref:`database url <environ-env-db-url>`
     - ``postgis://user:pass@host/db_name``
   * - :setting:`SLM_EMAIL_SERVER`
     - :ref:`email url <environ-env-email-url>`
     - ``smtp://localhost:25``
   * - :setting:`SERVER_EMAIL`
     - :class:`str`
     - ``noreply@yourdomain.org``
   * - :setting:`DEFAULT_FROM_EMAIL`
     - :class:`str`
     - ``noreply@yourdomain.org``
   * - :setting:`SECRET_KEY`
     - :class:`str`
     - ``abcdefghijklmnopqrstuvwxyz``
   * - :setting:`SLM_SECRETS_DIR`
     - :ref:`env_types_path`
     - ``./secrets``
   * - :setting:`SLM_LOG_LEVEL`
     - :class:`str`
     - ``TRACE|DEBUG|INFO|WARNING|ERROR|CRITICAL``
   * - :setting:`SLM_LOG_DIR`
     - :ref:`env_types_path`
     - ``./logs``
   * - :setting:`SLM_DEBUG_TOOLBAR`
     - :ref:`env_types_bool`
     - ``on|off``
   * - :setting:`SLM_IGS_STATION_NAMING`
     - :ref:`env_types_bool`
     - ``on|off``
   * - :setting:`SLM_SITE_NAME`
     - :ref:`env_types_bool`
     - ``slm.yourdomain.org``
   * - :setting:`SLM_ORG_NAME`
     - :ref:`env_types_bool`
     - ``Your Organization``
   * - :setting:`SLM_ADMIN_MAP`
     - :ref:`env_types_bool`
     - ``on|off``
   * - :setting:`SLM_SECURITY_DEFAULTS`
     - :ref:`env_types_bool`
     - ``on|off``
   * - :setting:`SLM_IGS_VALIDATION`
     - :ref:`env_types_bool`
     - ``on|off``
   * - :setting:`SLM_COORDINATE_MODE`
     - :class:`str`
     - ``INDEPENDENT|ECEF|LLH``
   * - :setting:`STATIC_ROOT`
     - :ref:`env_types_path`
     - ``path/to/static/from/basedir``
   * - :setting:`MEDIA_ROOT`
     - :ref:`env_types_path`
     - ``path/to/media/from/basedir``
   * - :setting:`SLM_THUMBNAIL_SIZE`
     - :class:`int`
     - 250
   * - :setting:`SLM_LEGACY_PLACEHOLDERS`
     - :ref:`env_types_bool`
     - ``on|off``
   * - :setting:`SLM_MAX_UPLOAD_SIZE_MB`
     - :class:`int`
     - 256

Types
-----

.. _env_types_path:

:class:`~pathlib.Path`
~~~~~~~~~~~~~~~~~~~~~~

We do not use :pypi:`django-environ`'s :class:`environ.Path` class. Instead we use the
:class:`~pathlib.Path` from the stdlib. If a setting is a path setting from Django_ core we
convert it to a :class:`str`.

**All relative paths will be resolved relative to** :setting:`BASE_DIR`

.. _env_types_bool:

:meth:`~environ.Env.bool`
~~~~~~~~~~~~~~~~~~~~~~~~~

Environment booleans will resolve to true if they make a case insensitive match to any of the
following strings:

.. code-block:: python

  ('true', 'on', 'ok', 'y', 'yes', '1')


.. _env_types_list:

:meth:`~environ.Env.list`
~~~~~~~~~~~~~~~~~~~~~~~~~

Lists should be comma delineated. E.g.: ``"item1,item2,item3"``


Environment Only Settings
-------------------------

These settings will not appear in ``django.conf.settings`` and are used to bootstrap parts
of the SLM before settings have finished resolving.

:envvar:`DJANGO_SETTINGS_MODULE`

This must be the import path to your entry settings files which will usually be the file that
imports ``slm.settings.root`` or, if the defaults with environment overrides are enough you may
set this directly to ``slm.settings.root``. Python_ must be able to import this file. If you are
getting import errors check your :envvar:`PYTHONPATH`.

.. envvar:: SLM_MANAGEMENT_FLAG

The SLM by default may behave slightly differently depending on if it is running in an http
web serving context or if it has been invoked on the command line. For example, by default we
change the log file names based on this so it is easier to see what work was being done in
process as opposed to during administrative tasks. When the ``SLM_MANAGEMENT_FLAG`` is set in the
process environment (not in an environment file), the SLM will set the
:setting:`SLM_MANAGEMENT_MODE` setting to ``True``.

.. _settings:

Settings
========

We list settings that are unique to the SLM, or settings from Django_ or
:ref:`our dependencies <dependencies>` where we have redefined the defaults.

``BASE_DIR`` ⚙️ 🚨
------------------
.. setting:: BASE_DIR

Default: ``Not Defined``

**This setting is required and must be an absolute path.** It is not an official Django setting,
but appears in the docs examples and is very common by convention. Think of it as the working
directory of your running SLM. Directories such as :setting:`SLM_LOG_DIR` will default to sub paths
of this directory.


``SLM_ENV`` ⚙️
--------------

.. setting:: SLM_ENV

Default: ``Not Defined``

The path to an optional environment file that will be loaded by the root settings. You
may specify this setting as an environment variable or as a file setting before you include
``slm.settings.root``.

``SLM_DATABASE`` ⚙️
-------------------

.. setting:: SLM_DATABASE

Default: ``postgis:///slm``

.. warning::

  The SLM requires that the default database be PostgreSQL_ with the PostGIS_ extension
  enabled.

This should be a :ref:`database url string <environ-env-db-url>`.

Use this setting to tell the SLM how to find it's default database. This is the database where
all the tables defined in :pypi:`igs-slm` will be stored, as well as any other tables that are
not :ref:`routed to other databases <django:topics-db-multi-db-routing>`.

This setting is optional, by default, the SLM will look for a database called ``slm``, and it
will use the username of the running process to connect to that database without a password over a
socket. This will work if postgres is configured for `peer authentication
<https://www.postgresql.org/docs/current/auth-peer.html>`_ and the running user has the correct
privileges.


``SLM_CACHE`` ⚙️
----------------
.. setting:: SLM_CACHE

Default: ``locmemcache://``

The default cache configuration to use specified as a :ref:`cache url <environ-env-cache-url>`.
When ``slm.settings.root`` is included configuration directives derived from this setting will
be added to any part of the ``default`` cache already specified.

``SLM_SITE_NAME`` ⚙️
--------------------

.. setting:: SLM_SITE_NAME

Default: ``ALLOWED_HOSTS[0]`` or ``""`` (Empty String)

The domain name of your site without the scheme. e.g. "slm.igs.org". If undefined, and
:setting:`ALLOWED_HOSTS` is not empty, the first entry in :setting:`ALLOWED_HOSTS` will be used.

When :django-admin:`routine deploy` or :django-admin:`set_site` is run this setting will be set
into the default :class:`~django.contrib.sites.models.Site`
:attr:`~django.contrib.sites.models.Site.domain` attribute.

``SLM_ORG_NAME`` ⚙️
-------------------
.. setting:: SLM_ORG_NAME

Default: ``"SLM"``

The name of your organization. This will appear in some of the HTML templates and email
communications. When :django-admin:`routine deploy` or :django-admin:`set_site` is run
this setting will be set into the default :class:`~django.contrib.sites.models.Site`
:attr:`~django.contrib.sites.models.Site.name` attribute.

``SLM_DEBUG_TOOLBAR`` ⚙️
------------------------
.. setting:: SLM_DEBUG_TOOLBAR

Default: :setting:`DEBUG`

**Never enable this in production**.

Enable or disable the :pypi:`django-debug-toolbar`. By default it will be enabled if
the :pypi:`django-debug-toolbar` is installed and :setting:`DEBUG` is true.

``SLM_IGS_VALIDATION`` ⚙️
-------------------------
.. setting:: SLM_IGS_VALIDATION

Default: ``True``

Use the default IGS log :ref:`validation rules <validation>`. If ``False`` no validation
will be performed on site log values other than basic database column type checks.

``SLM_COORDINATE_MODE`` ⚙️
--------------------------
.. setting:: SLM_COORDINATE_MODE

Default: ``INDEPENDENT``

Site logs contain position fields in both lat/lon/height and xyz (ECEF). By default the SLM will
allow users to specify these values indepenendently. Optionally it can be configured to compute
one from the other using the ITRF2020 ellipsoid parameters:

.. tabs::

    .. tab:: Visual

      .. list-table::
        :header-rows: 1
        :widths: 10 70

        * - :class:`~slm.defines.CoordinateMode`
          - Behavior
        * - :attr:`~slm.defines.CoordinateMode.INDEPENDENT`
          - User specifies station coordinates in ECEF and LLH seperately.
        * - :attr:`~slm.defines.CoordinateMode.ECEF`
          - User specifies station coordinates in ECEF, LLH coordinates are calculated by the system.
        * - :attr:`~slm.defines.CoordinateMode.LLH`
          - User specifies station coordinates in LLH, ECEF coordinates are calculated by the system.

    .. tab:: Code

      .. code-block:: python

        from slm.defines import CoordinateMode

        SLM_COORDINATE_MODE = CoordinateMode.ECEF


If using IGS validation rules there is also a validator that will throw warnings if these
coordinates differ by more than 1 meter in three dimensions.

``SLM_SECURITY_DEFAULTS`` ⚙️
----------------------------
.. setting:: SLM_SECURITY_DEFAULTS

Default: ``not`` :setting:`DEBUG`

Use the default production security settings form the SLM. This sets the following:

* :setting:`SECURE_SSL_REDIRECT` = True
* :setting:`CSRF_COOKIE_SECURE` = True
* :setting:`SESSION_COOKIE_SECURE` = True
* :setting:`SECURE_REFERRER_POLICY` = "origin"
* :setting:`X_FRAME_OPTIONS` = "DENY"


``SLM_ADMIN_MAP`` ⚙️
--------------------
.. setting:: SLM_ADMIN_MAP

Default: ``True``

Enable or disable the MapBox_ admin map in the SLM. Must be set in the environment
or prior to the inclusion of ``slm.settings.root``. You may also enable or disable
the admin map by adding or removing ``slm.map`` from :setting:`INSTALLED_APPS`.

``SLM_IGS_STATION_NAMING`` ⚙️
------------------------------
.. setting:: SLM_IGS_STATION_NAMING

Default: ``False``

Enable or disable the use of IGS naming rules for station names. If enabled, the defaults for
:setting:`SLM_STATION_NAME_REGEX` and :setting:`SLM_STATION_NAME_HELP` will be set to:

.. code-block:: python

    SLM_STATION_NAME_REGEX = r"[\w]{4}[\d]{2}[\w]{3}"
    SLM_STATION_NAME_HELP = _(
         "This is the 9 Character station name (XXXXMRCCC) used in RINEX 3 "
         "filenames Format: (XXXX - existing four character IGS station "
         "name, M - Monument or marker number (0-9), R - Receiver number "
         "(0-9), CCC - Three digit ISO 3166-1 country code)"
    )


``SLM_STATION_NAME_REGEX``
--------------------------
.. setting:: SLM_STATION_NAME_REGEX

Default: ``None``

Provide a regular expression to validate new station names against. By
default no validation occurs and station names may be any string up to
50 characters in length.

For example the IGS station name standard uses this regular expression:

.. code-block:: python

    SLM_STATION_NAME_REGEX = r"[\w]{4}[\d]{2}[\w]{3}"


``SLM_STATION_NAME_HELP``
-------------------------
.. setting:: SLM_STATION_NAME_HELP

Default: ``"The name of the station."``

Override the help text used for station name field. Useful if you have a custom
naming convention that requires explanation.

``SLM_MANAGEMENT_MODE``
-----------------------
.. setting:: SLM_MANAGEMENT_MODE

Default: ``True`` if :envvar:`SLM_MANAGEMENT_FLAG` is set, ``False`` otherwise.

This setting will be ``True`` when the SLM is running in the context of a management command
and ``False`` when running in the context of web serving. It is mostly used to make log file
changes.

``SLM_EMAIL_SERVER`` ⚙️
-----------------------
.. setting:: SLM_EMAIL_SERVER

Default: ``smtp://localhost:25``

An :ref:`email server url <environ-env-email-url>` that will handle outgoing email traffic.
This setting will be used to set the following Django settings:

* :setting:`EMAIL_BACKEND`
* :setting:`EMAIL_FILE_PATH`
* :setting:`EMAIL_HOST_USER`
* :setting:`EMAIL_HOST_PASSWORD`
* :setting:`EMAIL_HOST`
* :setting:`EMAIL_PORT`
* :setting:`EMAIL_USE_TLS`
* :setting:`EMAIL_USE_SSL`

``SERVER_EMAIL`` ⚙️
-------------------
.. setting:: SERVER_EMAIL

Default: ``noreply@domain`` where ``domain`` is :setting:`SLM_SITE_NAME` or ``localhost``

We provide a more reasonable default than Django_'s :setting:`django:SERVER_EMAIL`.

``DEFAULT_FROM_EMAIL`` ⚙️
-------------------------
.. setting:: DEFAULT_FROM_EMAIL

Default: :setting:`SERVER_EMAIL`

We provide a more reasonable default than Django_'s :setting:`django:DEFAULT_FROM_EMAIL`.

``WSGI_APPLICATION`` ⚙️
-----------------------
.. setting:: WSGI_APPLICATION

Default: ``slm.wsgi.application``

We set a default for :setting:`django:WSGI_APPLICATION` that works if *either*:

1. The :envvar:`DJANGO_SETTINGS_MODULE` is ``slm.settings.root``
2. The :envvar:`DJANGO_SETTINGS_MODULE` is set in the environment of the process that loads Django
   for web serving.
3. You are not using WSGI - e.g. in a local development or debug context using
   :django-admin:`runserver`.

This should work for most installations, only override it if it does not.

``ALLOWED_HOSTS`` ⚙️
--------------------
.. setting:: ALLOWED_HOSTS

Default:
 * ``DEBUG=False``: ``[`` :setting:`SLM_SITE_NAME` ``]``
 * ``DEBUG=True``: ``["localhost", "127.0.0.1", "[::1]"]``

We override the empty default of :setting:`django:ALLOWED_HOSTS` with reasonable options.

.. tip::

  In production you will likely have to add the IP address of your production machine to the list.

``ROOT_URLCONF``
----------------
.. setting:: ROOT_URLCONF

Default: ``slm.settings.urls``

We override the Django_ default setting :setting:`django:ROOT_URLCONF` of ``not defined``.
With the basic SLM urls. If you need to add any urls you should override this and provide your
own urls python file.

``STATIC_ROOT`` ⚙️
------------------
.. setting:: STATIC_ROOT

Default: :setting:`BASE_DIR` ``/static``

**This is where all statically served file asserts will live. These files are normally served by
the webserver above Django on the stack.**

We override the Django_ default setting :setting:`django:STATIC_ROOT` of ``None``. If the directory
does not exist and it is a sub directory of :setting:`BASE_DIR` the SLM will create it.

``MEDIA_ROOT`` ⚙️
-----------------
.. setting:: MEDIA_ROOT

Default: :setting:`BASE_DIR` ``/media``

**This is where all uploaded and dynamically generated file artifacts will be stored.**

We override the Django_ default setting :setting:`django: MEDIA_ROOT` of ``None``. If the directory
does not exist and it is a sub directory of :setting:`BASE_DIR` the SLM will create it.

``SLM_SECRETS_DIR`` ⚙️
----------------------
.. setting:: SLM_SECRETS_DIR

Default: :setting:`BASE_DIR` ``/secrets``

The directory where secrets are kept. If there is a file named `secret_key` in this directory it
will be read into :setting:`SECRET_KEY` if that setting is unset. If that file does not exist
the SLM will generate a random key on startup.

``SLM_LOG_LEVEL`` ⚙️
--------------------
.. setting:: SLM_LOG_LEVEL

Default:
  * DEBUG=True: ``DEBUG``
  * DEBUG=False: ``INFO``

Set the default log level for loggers. This may be any of the
:ref:`standard library logging levels <python:levels>` and also ``TRACE``.

``SLM_LOG_DIR`` ⚙️
------------------
.. setting:: SLM_LOG_DIR

The directory where file logs will be stored. If this directory does not exist but is a sub path
of :setting:`BASE_DIR` it will be created.

``LOGGING``
-----------
.. setting:: LOGGING

We use the :doc:`python stdlib logging module <python:howto/logging>` for logging. The Django_
documentation also :doc:`covers logging <django:howto/logging>`. See also Django's
:setting:`django:LOGGING` and :setting:`django:LOGGING_CONFIG`.

Our default configuration has the following qualities:

* Most loggers will be set to the :setting:`SLM_LOG_LEVEL` level. Some particularly noisy or
  unnecessary loggers will be set to higher levels.
* A :class:`~logging.handlers.TimedRotatingFileHandler` file handler will be created that rotates
  files every night at midnight and keeps 14 days worth of logs. The logs will be stored at
  :setting:`SLM_LOG_DIR` / :setting:`SLM_SITE_NAME`.log
* An :class:`~django.utils.log.AdminEmailHandler` will be created that emails :setting:`ADMINS`
  with an error report anytime a log statement at ``ERROR`` or higher is issued.
* If :setting:`SLM_MANAGEMENT_MODE` is on, log files will have ``_manage`` appended to their names.

``MESSAGE_LEVEL``
-----------------
.. setting:: MESSAGE_LEVEL

Default:

  * DEBUG=True: ``DEBUG``
  * DEBUG=False: ``INFO``

We override the base Django_ default setting :setting:`django:MESSAGE_LEVEL` of ``INFO``.

``SLM_ALERT_COLORS``
--------------------
.. setting:: SLM_ALERT_COLORS

Default:

.. tabs::

    .. tab:: Visual

      .. list-table::
        :header-rows: 1
        :widths: 40 40

        * - :class:`slm.defines.AlertLevel`
          - Color
        * - :attr:`~slm.defines.AlertLevel.NOTICE`
          - :color-swatch:`#12CAF0`
        * - :attr:`~slm.defines.AlertLevel.WARNING`
          - :color-swatch:`#E3AA00`
        * - :attr:`~slm.defines.AlertLevel.ERROR`
          - :color-swatch:`#DD3444`

    .. tab:: Code

      .. code-block:: python

        from slm.defines import AlertLevel

        SLM_ALERT_COLORS = {
            AlertLevel.NOTICE: "#12CAF0",
            AlertLevel.WARNING: "#E3AA00",
            AlertLevel.ERROR: "#DD3444",
        }

Customize the color used in the web interface to represent alerts at different levels.


``SLM_STATUS_COLORS``
---------------------
.. setting:: SLM_STATUS_COLORS

Default:

.. tabs::

    .. tab:: Visual

      .. list-table::
        :header-rows: 1
        :widths: 40 40

        * - :class:`slm.defines.SiteLogStatus`
          - Color
        * - :attr:`~slm.defines.SiteLogStatus.FORMER`
          - :color-swatch:`#3D4543`
        * - :attr:`~slm.defines.SiteLogStatus.SUSPENDED`
          - :color-swatch:`#E0041A`
        * - :attr:`~slm.defines.SiteLogStatus.PROPOSED`
          - :color-swatch:`#913D88`
        * - :attr:`~slm.defines.SiteLogStatus.UPDATED`
          - :color-swatch:`#0079AD`
        * - :attr:`~slm.defines.SiteLogStatus.PUBLISHED`
          - :color-swatch:`#0D820D`
        * - :attr:`~slm.defines.SiteLogStatus.EMPTY`
          - :color-swatch:`#D3D3D3`

    .. tab:: Code

      .. code-block:: python

        from slm.defines import SiteLogStatus

        SLM_STATUS_COLORS = {
            SiteLogStatus.FORMER: "#3D4543",
            SiteLogStatus.SUSPENDED: "#E0041A",
            SiteLogStatus.PROPOSED: "#913D88",
            SiteLogStatus.UPDATED: "#0079AD",
            SiteLogStatus.PUBLISHED: "#0D820D",
            SiteLogStatus.EMPTY: "#D3D3D3"
        }

Customize the color used in the web interface to represent site log status states.

``SLM_FILE_COLORS``
--------------------
.. setting:: SLM_FILE_COLORS

Default:

.. tabs::

    .. tab:: Visual

      .. list-table::
        :header-rows: 1
        :widths: 40 40

        * - :class:`slm.defines.SiteFileUploadStatus`
          - Color
        * - :attr:`~slm.defines.SiteFileUploadStatus.UNPUBLISHED`
          - :color-swatch:`#0079AD`
        * - :attr:`~slm.defines.SiteFileUploadStatus.PUBLISHED`
          - :color-swatch:`#0D820D`
        * - :attr:`~slm.defines.SiteFileUploadStatus.INVALID`
          - :color-swatch:`#8b0000`
        * - :attr:`~slm.defines.SiteFileUploadStatus.WARNINGS`
          - :color-swatch:`#E3AA00`
        * - :attr:`~slm.defines.SiteFileUploadStatus.VALID`
          - :color-swatch:`#0D820D`

    .. tab:: Code

      .. code-block:: python

        from slm.defines import SiteFileUploadStatus

        SLM_FILE_COLORS = {
            SiteFileUploadStatus.UNPUBLISHED: "#0079AD",
            SiteFileUploadStatus.PUBLISHED: "#0D820D",
            SiteFileUploadStatus.INVALID: "#8b0000",
            SiteFileUploadStatus.WARNINGS: "#E3AA00",
            SiteFileUploadStatus.VALID: "#0D820D"
        }

Customize the color used in the web interface to represent file upload status states.

``SLM_FILE_ICONS``
--------------------
.. setting:: SLM_FILE_ICONS

Default:

.. tabs::

    .. tab:: Visual

      .. list-table::
        :header-rows: 1
        :widths: 40 40

        * - Mime type
          - Icon
        * - ``zip``
          - :css-icon:`bi bi-file-zip:24`
        * - ``x-tar``
          - :css-icon:`bi bi-file-zip:24`
        * - ``plain``
          - :css-icon:`bi bi-filetype-txt:24`
        * - ``jpeg``
          - :css-icon:`bi bi-filetype-jpg:24`
        * - ``svg+xml``
          - :css-icon:`bi bi-filetype-svg:24`
        * - ``xml``
          - :css-icon:`bi bi-filetype-xml:24`
        * - ``json``
          - :css-icon:`bi bi-filetype-json:24`
        * - ``png``
          - :css-icon:`bi bi-filetype-png:24`
        * - ``tiff``
          - :css-icon:`bi bi-filetype-tiff:24`
        * - ``pdf``
          - :css-icon:`bi bi-filetype-pdf:24`
        * - ``gif``
          - :css-icon:`bi bi-filetype-gif:24`
        * - ``csv``
          - :css-icon:`bi bi-filetype-csv:24`
        * - ``bmp``
          - :css-icon:`bi bi-filetype-bmp:24`
        * - ``vnd.openxmlformats...``
          - :css-icon:`bi bi-filetype-doc:24`
        * - ``msword``
          - :css-icon:`bi bi-filetype-doc:24`


    .. tab:: Code

      .. code-block:: python

        SLM_FILE_ICONS = {
            "zip": "bi bi-file-zip",
            "x-tar": "bi bi-file-zip",
            "plain": "bi bi-filetype-txt",
            "jpeg": "bi bi-filetype-jpg",
            "svg+xml": "bi bi-filetype-svg",
            "xml": "bi bi-filetype-xml",
            "json": "bi bi-filetype-json",
            "png": "bi bi-filetype-png",
            "tiff": "bi bi-filetype-tiff",
            "pdf": "bi bi-filetype-pdf",
            "gif": "bi bi-filetype-gif",
            "csv": "bi bi-filetype-csv",
            "bmp": "bi bi-filetype-bmp",
            "vnd.openxmlformats-officedocument.wordprocessingml.document": "bi bi-filetype-doc",
            "msword": "bi bi-filetype-doc",
        }

Customize the icons used in the web interface to represent specific file mimetypes. These icons
will render as:

.. code-block:: html

    <i class="{icon}"></i>

``SLM_THUMBNAIL_SIZE`` ⚙️
-------------------------
.. setting:: SLM_THUMBNAIL_SIZE

Default: ``250``

The width in pixels of thumbnail previews of images generated by the SLM.


``SLM_LEGACY_PLACEHOLDERS`` ⚙️
------------------------------
.. setting:: SLM_LEGACY_PLACEHOLDERS

Default: ``True``

If true, include a final placeholder section in renderings of the ASCII legacy formats
of the site logs.

``SLM_MAX_UPLOAD_SIZE_MB`` ⚙️
-----------------------------
.. setting:: SLM_MAX_UPLOAD_SIZE_MB

Default: ``100``

The maximum allowed upload file size. Arbitrary files may be attached to stations.

``SLM_HTTP_PROTOCOL``
---------------------
.. setting:: SLM_HTTP_PROTOCOL

Default:

  * DEBUG=True: ``http``
  * DEBUG=False: ``https``

In the event the SLM needs to build a link without a request object to determine which http scheme
it should use, use this scheme.

``SLM_PERMISSIONS``
-------------------
.. setting:: SLM_PERMISSIONS

Default: ``slm.authentication.default_permissions``

This setting tells the SLM which permissions are pertinent to its functionality.

We use Django_'s :ref:`permission framework <topics/auth/default:permissions and authorization>`
to control user access to certain functionality. If you wish to add your own permissions you may
set this directive to the import path of a function that returns a
:class:`~django.contrib.auth.models.Permission` :class:`~django.db.models.query.QuerySet`. The SLM
will use this in the admin as the set of user permissions that should be offered on the user change
forms. Superfluous permissions will be hidden.

``SLM_DEFAULT_PERMISSION_GROUPS``
---------------------------------
.. setting:: SLM_DEFAULT_PERMISSION_GROUPS

Default: ``{"Agency Manager": ["propose_sites", "moderate_sites"]}``

We use the Django_ :ref:`permission framework <topics/auth/default:permissions and authorization>`
to open up certain functionality to users.

This setting creates named groups of permissions that are shown on the user admin forms.
Permissions groups can be thought of as user roles. We create an ``Agency Manager`` role by default
that allows its members to propose new sites for their agency and publish (moderate) site logs for
sites belonging to their agency.

This setting must be a dictionary where the group name is the key and the values are lists of
:attr:`permission code names <django.contrib.auth.models.Permission.codename>`.

``SLM_PRELOAD_SCHEMAS``
-----------------------
.. setting:: SLM_PRELOAD_SCHEMAS

Default:

  * :setting:`DEBUG` or :setting:`SLM_MANAGEMENT_MODE`: ``[]`` (Empty List)
  * not :setting:`DEBUG`: ``list(GeodesyMLVersion)``

The xsd schemas that should be preloaded on start - if a schema is used that is not preloaded it
will be lazily loaded which can take some time and will prolong the request. It can be useful to
disable this during testing to reduce load times. It is recommended to leave this set to the
default setting in production.

When set to a list these should be instances of :class:`~slm.defines.GeodesyMLVersion`.

This setting may also be a falsey value, in which case no preloads will be attempted.

``SLM_EMAILS_REQUIRE_LOGIN``
----------------------------
.. setting:: SLM_EMAILS_REQUIRE_LOGIN

Default: ``True``

By default the SLM will not send moderation related emails to user accounts who have never logged
in, set this to False to disable this behavior. This does not apply to account related emails like
password reset requests. Moderation emails include notices like site log review requests and
publish events.


.. TODO? SLM_URL_MOUNTS

``SLM_FILE_DOMAIN``
-------------------
.. setting:: SLM_FILE_DOMAIN

Default: ``None``

Sets the domain used to generate links to the SLM station attachments including images and files.
Any standalone artifacts produced by the slm that include links to files served by the SLM will
use this domain as the stem. If empty the default site domain will be used. You probably do not
need to set this field unless you are serving files off a different instance than the instance
that generates serialized artifacts.


``SLM_AUTOMATED_ALERTS``
------------------------
.. setting:: SLM_AUTOMATED_ALERTS

Use this setting to control when automated email alert system.

.. TODO::

  Describe this setting.

``SLM_VALIDATION_BYPASS_BLOCK``
-------------------------------
.. setting:: SLM_VALIDATION_BYPASS_BLOCK

Default: ``False``

Toggling this off will prevent any validation configured to block edit saves from doing so -
instead flags will be issued.


``SLM_REQUIRED_SECTIONS_TO_PUBLISH``
------------------------------------
.. setting:: SLM_REQUIRED_SECTIONS_TO_PUBLISH

Default:

.. code-block:: python

  SLM_REQUIRED_SECTIONS_TO_PUBLISH = [
      "siteform",
      "siteidentification",
      "sitelocation",
      "sitereceiver",
      "siteantenna",
      "siteoperationalcontact"
  ]

The minimum set of completed site log sections required to publish a log for the first time. Must
be a list of site log section model names.

``SLM_DATA_VALIDATORS``
-----------------------
.. setting:: SLM_DATA_VALIDATORS

Use this setting to control how site log sections are validated. Also see
:setting:`SLM_IGS_VALIDATION`.

.. TODO::

  Describe this setting.
