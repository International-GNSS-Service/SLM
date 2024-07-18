.. include:: refs.rst

============
Installation
============

The `SLM` is both a Django_ app and a fully deployable website. Most users of the SLM
will want to customize certain aspects of it. To facilitate that we will use the
:ref:`slm-startproject` bundled command to generate a scaffold to build off of
(not unlike `Django's startproject <https://docs.djangoproject.com/en/stable/ref/django-admin/#django-admin-startproject>`_) .
But first we must install some dependencies.

There are generally three deployment contexts under which you might wish to run an SLM.
Hereafter, we will use the following terminology to describe these deployments:

* **develop** - A deployment used for development. You might run this on a local server,
  but typically each developer will have their own local instance running on their
  own machine connected to their own database so they can experiment without interfering
  with other developers.
* **production** - This is your live instance of the SLM that is used for your real world
  data.
* **staging** - Depending on your operational requirements you may wish to run a staging
  server with an identical configuration to your production server to test out updates
  before deploying them to production.

Dependencies
############

Most of the dependencies will be the same between different deployments, but production will
require a webserver and other production specific requirements. The following table lists
the major dependencies that will most likely need to be manually installed depending on your
environment(s):

.. list-table:: Manually Installed Software
   :header-rows: 1

   * - Dependency
     - Version
     - Required
     - Description

   * - Python_
     - >=3.8
     - ✅
     - Programming language runtime.
   * - PostgreSQL_
     - >=12
     - ✅
     - Relational Database (RDBMS)
   * - PostGIS_
     - >=3.4
     - ✅
     - Geographic information system extension to PostgreSQL_.
   * - Django_ & GeoDjango_
     - >=4.2
     - ✅
     - Will be installed automatically, but GeoDjango_ has external depdendencies that may need to
       be installed manually.
   * - pgAdmin_
     - >=7.0
     -
     - A graphical PostgreSQL management utility. Recommended for local development.
   * - Poetry_
     - >=1.8
     -
     - A python build and package management system. Used by :ref:`slm-startproject`
   * - pyenv_
     - >=2.3
     -
     - A python management system. Not required but recommended for local development.

|

Platform specific Installation guidance.
----------------------------------------

.. tabs::

    .. tab:: OSX

       * By far and away the easiest way to install PostgreSQL_ and PostGIS_ in OSX is to use
         Postgres.app_. This will also install all the necessary GeoDjango_ dependencies.
       * The GeoDjango_ documentation has
         `a few additional instructions <https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/#postgres-app>`_
       * OSX uses z-shell_ by default. If you would like to enable tab completions for slm
         management commands, you will want to use homebrew_ to
         `install z-shell completions <https://django-typer.readthedocs.io/en/latest/shell_completion.html#osx>`_.


    .. tab:: Windows

       * Follow the `GeoDjango documentation to install all the necessary dependencies <https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/#windows>`_.
       * Windows uses the `Enterprise DB (EDB) installer <https://www.postgresql.org/download/windows/>`_
         to install PostgreSQL_.
       * Here's a `helpful video <https://video.osgeo.org/w/57e27085-6352-43e6-b64a-c29c1dcda8ee>`_.
       * If you want `shell tab completions <https://django-typer.readthedocs.io/en/latest/shell_completion.html>`_
         to work for your management commands, you will probably want to
         `install PowerShell <https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows>`_.


    .. tab:: Linux

       * All dependencies should be readily installable from your flavor's package manager. If
         needed, refer to the GeoDjango documentation for
         `help building the geospatial library dependencies <https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/geolibs/>`_.
       * You will probably want to use the command line utility psql_ instead of pgAdmin_ for
         database management.

.. tip::

       If you are having trouble with your GeoDjango_ installation, please refer to the
       `troubleshooting guide <https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/#troubleshooting>`_.


.. _slm-startproject:

Start Project
#############

To get up and running quickly with your customized SLM deployment we bundle a command called
slm-startproject_ that will scaffold out a directory structure and settings files for you to start
working with. Before running slm-startproject_ you will need to have installed all of GeoDjango_'s
dependencies as well as PostgreSQL_ and PostGIS_ and Poetry_. You do not need to install Django_
itself yet though.

(1) Install igs-slm_
--------------------

    .. code:: bash

        ?> pip install igs-slm

You also have the option of working with our development version from github, but unless you have
a compeling reason to do so you should use the release on pypi.

    .. code:: bash

        ?> git clone https://github.com/International-GNSS-Service/SLM.git
        ?> cd SLM
        ?> poetry install

Now you should have a command available on your terminal called slm-startproject_ and when you
run

.. code:: bash

  ?> slm-startproject --help

you should see this:


.. typer:: slm.bin.startproject:app
    :prog: slm-starproject
    :theme: dark
    :width: 70

|

(2) Run slm-startproject
------------------------

Before running the command you should decide what your production url will be. If it were
https://network.example.com we might proceed as follows to create the files in a directory called
network. You will be prompted to supply the CLI arguments. For the simplest deployment, after
the first question you can just hit enter to accept the defaults:

  .. code-block::

    ?> slm-startproject network.example.com ./
    What is the name of your organization? []: Example
    What should we name your project directory? [{subdomain}]: <enter>
    What should we name your installable wheel? [{project_dir}]: <enter>
    What is the name of your site? [{subdomain}]: <enter>
    Where should files live in production? [/var/www/{site}/production]: <enter>
    What should we call your custom Django app? [{org}_extensions]: <enter>
    Install the mapbox map app? [y/N]: <enter>
    Use IGS sitelog validation defaults? [y/N]: <enter>

**slm-startproject** will create a directory structure that looks like this:

  .. code-block:: text

    network
    ├── example_extensions             # a Django app you can use to extend SLM
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── management
    │   │   ├── __init__.py
    │   │   └── commands               # your custom management commands go here
    │   │       ├── __init__.py
    │   │       └── import_archive.py  # extend/override SLM's import_archive command
    │   ├── migrations
    │   │   └── __init__.py
    │   ├── models.py
    │   ├── templates
    │   │   └── slm
    │   │       └── base.html          # override the base template to change branding
    │   ├── urls.py                    # add any custom URLs here
    │   └── views.py
    ├── pyproject.toml                 # package, dependencies and tools configured here
    └── sites                          # top level directory for different instance configs
        ├── __init__.py
        └── network                    # django settings for the network subdomain
            ├── __init__.py
            ├── base.py                # common settings for all network deployments
            ├── develop                # DJANGO_SETTINGS_MODULE="sites.network.develop"
            │   ├── __init__.py        # the develop deployment settings
            │   ├── local.py
            │   └── wsgi.py
            ├── manage.py              # this manage script gets packaged as 'network'
            ├── production             # DJANGO_SETTINGS_MODULE="sites.network.production"
            │   ├── __init__.py        # the production deployment settings
            │   └── wsgi.py
            ├── urls.py                # root url config: bring in URLs from apps here
            └── validation.py          # configure sitelog validation here

.. tip::

  It was worth spending some time to familiarize yourself with these files. Many are commented
  or have links to online resources for further explanation.

.. warning::

  When using the develop deployment, the logs, media, static files and secrets will be written
  to the develop settings directory. **You will want to exclude these directories from version
  control.**


(3) Create environment & database
---------------------------------

* Use either psql_ or pgAdmin_ to create the database that **slm-startproject** instructs you to.
  In our example this database would be named 'network'.

* Use poetry to install the virtual environment then activate it. We also recommend configuring
  poetry to create virtual environments in the same directory as your project:

    .. code-block:: bash

      ?> poetry config virtualenvs.in-project true
      ?> poetry install
      ?> source .venv/bin/activate


.. _import_sitelogs:

(4) Import Existing Logs and Deploy
-----------------------------------

The SLM ships with a number of :ref:`pre-defined routines <routines>`. If you do not have any
existing logs to import you'll probably just want to run :ref:`routine_deploy`. Otherwise gather
your logs into a single directory or tar file and run the :ref:`routine_install` routine:

  .. code-block:: bash

    ?> <slm> routine install

**<slm> is the name of your management script. In our example it would be called 'network'.**

The data import will both generate logs and record import errors and warnings as alerts and
validation flags in the database so you can manually go through the web interface and correct any
errors.

(5) Run the Development Server
------------------------------

You should now be able to start up the development server and see data in your SLM instance.

  .. code-block:: bash

    ?> <slm> runserver
    Performing system checks...

    System check identified no issues (1 silenced).
    Django version 4.2.14, using settings 'sites.<slm>.develop'
    Starting development server at http://127.0.0.1:8000/
    Quit the server with CONTROL-C.

In addition to the front end interface where site logs are edited, moderated and published. We use
the `Django admin for a more direct access to system data <http://127.0.0.1:8000/admin>`_. This is
where we control permissions and make site adjustments. You may also add users and agencies and set
their permissions through the admin.

.. tip::

  Refer to :ref:`operations` for advice on production deployments.

.. _fast_hosting:

Fast Hosting
############

.. todo::
       Instructions for quickly deploying to a hosting service..
