.. include:: refs.rst

.. _commands:

========
Commands
========

The SLM provides some :doc:`Django management commands <django:ref/django-admin>` out of the box.
Management commands are a standard way to implement routine tasks that are installable with your
site and may interface with the database using a fully bootstrapped Django stack configured for
your site.

The SLM management commands are implemented using :doc:`django-typer:index` which extends
Django's base command to work with the Typer_ CLI library. This also gives us some convenient
extra features like :doc:`shell tab completions <django-typer:shell_completion>`.

Most of our SLM management commands manipulate data in ways that would be difficult or too time
consuming through the web interface. We also provide some commands that perform backup and restore
operations.

We use :doc:`django-routines:index` to provide a few named routines to execute batched groups of
commands for typical work flows that are required during installation and update deployment.

Management commands are invoked using a Django :doc:`manage script <django:ref/django-admin>`. If
using :django-admin:`startproject` this script will be called ``manage.py``. If using our
:ref:`slm-startproject` the manage script will be named after your site and indicated in the output
report. Manage scripts are typically simple and can be thought of as the main of Django. They
bootstrap the Django stack configured for your site and then run the command indicated by the CLI
arguments.

Here's an example of a typical SLM management script:

.. code-block:: python
    :caption: manage.py

    import os
    import sys

    # Use SLM_DEPLOYMENT environment variable to switch between deployments. In
    # production you may want to just set this to "production" in your
    # administrative user's shell profile
    def main(
        default_settings: str = \
        f"sites.<site>.{os.environ.get('SLM_DEPLOYMENT', 'develop')}"
    ):
        """Run administrative tasks."""

        # SLM configures loggers differently when running management commands
        # so we can distinguish logs on the server that were from requests or
        # admin tasks. This environment variable is used to signal that the SLM
        # runtime is in management mode.
        if len(sys.argv) > 1 and sys.argv[1] != "runserver":
            os.environ['SLM_MANAGEMENT_FLAG'] = 'ON'

        # Django bootstraps off the settings file defined in this import path.
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', default_settings)

        try:
            from django.core.management import execute_from_command_line
        except ImportError as exc:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            ) from exc
        execute_from_command_line(sys.argv)


    if __name__ == "__main__":
        main()


.. note::

    In the command helps below, replace <slm> with the name of your manage script.


.. list-table:: SLM Management Commands
   :header-rows: 1

   * - Command
     - Short Description
   * - :django-admin:`check_upgrade`
     - Check that the upgrade that is about to be run is safe.
   * - :django-admin:`build_index`
     - Re-build the head of the file index from the current published database state.
   * - :django-admin:`generate_sinex`
     - Generate a SINEX file from the published database state.
   * - :django-admin:`head_from_index`
     - Import data into the database from the latest site log(s) from the file index.
   * - :django-admin:`import_archive`
     - Add site log files to the file index.
   * - :django-admin:`import_equipment`
     - Import equipment codes for antennas, receivers and radomes from another SLM.
   * - :django-admin:`set_site`
     - Set Django Site model fields based on your settings file.
   * - :django-admin:`sitelog`
     - Generate a serialized site log in a given format from the current database state.
   * - :django-admin:`synchronize`
     - Synchronize any denormalized state in the database.
   * - :django-admin:`validate_db`
     - Re-run all site log validation routines on the given (or all) stations.

.. list-table:: SLM Management Routines
   :header-rows: 1

   * - Routine
     - Short Description
   * - :django-admin:`routine deploy`
     - Run a collection of commands commonly required when updating SLM code in production.
   * - :django-admin:`routine import`
     - Run a collection of commands commonly required when importing an external archive of site
       log data.
   * - :django-admin:`routine install`
     - Run a collection of commands commonly required when installing to a fresh database. This
       runs both the :django-admin:`routine deploy` and :django-admin:`routine import` subroutines.

In addition to the SLM specific commands, the common Django commands you will need to use are:

.. list-table:: Django Management Commands
   :header-rows: 1

   * - Command
     - Short Description
   * - :django-admin:`makemigrations`
     - Generate migration files from your models that will update the database structure to
       reflect your code base.
   * - :django-admin:`migrate`
     - Run any unapplied migration scripts on the database.
   * - :django-admin:`collectstatic`
     - Gather all static artifacts from Django apps and move them into STATIC_ROOT_.
   * - :django-admin:`shell`
     - Launch an interactive shell with your site bootstrapped and a live connection to the
       database.

Commands installed by third party apps that may also be useful or necessary:

.. list-table:: Third Party Management Commands
   :header-rows: 1

   * - Command
     - Short Description
   * - renderstatic_
     - Generate static artifacts from your code/configuration. This mostly includes JavaScript
       artifacts. See :django-admin:`routine deploy`
   * - shellcompletion_
     - Install/test shell tab completion for all management commands.

|

check_upgrade
-------------

.. django-admin:: check_upgrade

.. automodule:: slm.management.commands.check_upgrade

.. typer:: slm.management.commands.check_upgrade.Command::typer_app
    :prog: <slm> check_upgrade
    :theme: dark
    :preferred: svg
    :convert-png: latex

|

build_index
-----------

.. django-admin:: build_index

.. automodule:: slm.management.commands.build_index

.. typer:: slm.management.commands.build_index.Command::typer_app
    :prog: <slm> build_index
    :theme: dark
    :preferred: svg
    :convert-png: latex

|

generate_sinex
--------------

.. django-admin:: generate_sinex

.. automodule:: slm.management.commands.generate_sinex

.. typer:: slm.management.commands.generate_sinex.Command::typer_app
    :prog: <slm> generate_sinex
    :theme: dark

|

head_from_index
---------------

.. django-admin:: head_from_index

.. automodule:: slm.management.commands.head_from_index

.. typer:: slm.management.commands.head_from_index.Command::typer_app
    :prog: <slm> head_from_index
    :theme: dark

|

import_archive
--------------

.. django-admin:: import_archive

.. automodule:: slm.management.commands.import_archive

.. typer:: slm.management.commands.import_archive.Command::typer_app
    :prog: <slm> import_archive
    :theme: dark

|

import_equipment
----------------

.. django-admin:: import_equipment

.. automodule:: slm.management.commands.import_equipment

.. typer:: slm.management.commands.import_equipment.Command::typer_app
    :prog: <slm> import_equipment
    :theme: dark


manufacturers
~~~~~~~~~~~~~

.. django-admin:: import_equipment manufacturers

.. typer:: slm.management.commands.import_equipment.Command::typer_app:manufacturers
    :prog: <slm> import_equipment manufacturers
    :theme: dark


antennas
~~~~~~~~

.. django-admin:: import_equipment antennas

.. typer:: slm.management.commands.import_equipment.Command::typer_app:antennas
    :prog: <slm> import_equipment antennas
    :theme: dark


receivers
~~~~~~~~~

.. django-admin:: import_equipment receivers

.. typer:: slm.management.commands.import_equipment.Command::typer_app:receivers
    :prog: <slm> import_equipment receivers
    :theme: dark

radomes
~~~~~~~

.. django-admin:: import_equipment radomes

.. typer:: slm.management.commands.import_equipment.Command::typer_app:radomes
    :prog: <slm> import_equipment radomes
    :theme: dark

|

set_site
--------

.. django-admin:: set_site

.. automodule:: slm.management.commands.set_site

.. typer:: slm.management.commands.set_site.Command::typer_app
    :prog: <slm> set_site
    :theme: dark

|

sitelog
-------

.. django-admin:: sitelog

.. automodule:: slm.management.commands.sitelog

.. typer:: slm.management.commands.sitelog.Command::typer_app
    :prog: <slm> sitelog
    :theme: dark

legacy
~~~~~~~~~~~~~

.. django-admin:: sitelog legacy

.. typer:: slm.management.commands.sitelog.Command::typer_app:legacy
    :prog: <slm> sitelog legacy
    :theme: dark


xml
~~~

.. django-admin:: sitelog xml

.. typer:: slm.management.commands.sitelog.Command::typer_app:xml
    :prog: <slm> sitelog xml
    :theme: dark

|

synchronize
-----------

.. django-admin:: synchronize

.. automodule:: slm.management.commands.synchronize

.. typer:: slm.management.commands.synchronize.Command::typer_app
    :prog: <slm> synchronize
    :theme: dark

|

validate_db
-----------

.. django-admin:: validate_db

.. automodule:: slm.management.commands.validate_db

.. typer:: slm.management.commands.validate_db.Command::typer_app
    :prog: <slm> validate_db
    :theme: dark


|

.. _routines:

Routines
--------

Routines are groupings of commands that can be configured in settings and run together.
They are defined using the app django-routines_. The commands that are run as part of a routine
can be added to or subtracted from in customized deployments of the SLM. Out of the box the
SLM provides the following routines:

deploy
~~~~~~

.. django-admin:: routine deploy

The deploy routine includes a collection of commands that should be run each time an updated
version of the SLM code base is deployed on a system. These commands will do things
like bring the database structure into compliance with the code base, render any static
artifacts and copy those artifacts to where the web server expects.

.. warning::

  **deploy** does not run :django-admin:`makemigrations` because these files should be checked into version
  control and we do not want to accidentally generate files and apply them to the database in
  production. This would likely cause conflicting migration files to be generated in development
  and production.

  :django-admin:`migrate` will warn if the code is out of sync with the database structure. And you should
  always run :django-admin:`makemigrations` before packaging a new version of your software for deployment.

If the SLM validation configuration has changed you will likely want to run deploy with the
``--re-validate`` flag to run the updated routines:

  .. code-block:: bash

    <slm> routine deploy --re-validate

You may also wish to not re-validate everything and instead let the new validation routines
be run each time a stations data is updated.

.. typer:: django_routines.management.commands.routine.Command::typer_app::deploy
    :prog: <slm> routine deploy
    :theme: red_sands

|

import
~~~~~~~

.. django-admin:: routine import

The import routine runs a collection of data import commands you will likely need to run when
importing an archive of old site logs.

These commands will import the serialized site logs and attempt to read the data out of those
logs and store them in the database.

.. note::

  This import process will import equipment codes from the IGS. You will also be prompted for
  a path to an archive of historical site logs (either a directory or tar file).

  If you need a more bespoke import process you should run each of these import routines
  separately with customized parameters.

.. typer:: django_routines.management.commands.routine.Command::typer_app::import
    :prog: <slm> routine import
    :theme: red_sands

|

install
~~~~~~~

.. django-admin:: routine install

The install routine runs the initial :django-admin:`routine deploy` routine as well as the
:django-admin:`routine import` routine. In addition it asks you to create a superuser account.

Run this routine on a fresh database if you have a bunch of site logs to import.

.. typer:: django_routines.management.commands.routine.Command::typer_app::install
    :prog: <slm> routine install
    :theme: red_sands
