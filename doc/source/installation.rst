.. include:: refs.rst

.. _installation:

============
Installation
============

Depending on your requirements you may wish to dive into the details and build out a
fully customizable :ref:`manual installation <manual_install>` of the SLM or you may just
want to get up and running in development or production as fast as possible with a
:ref:`containerized build <containerization>`. If containers are familiar to you we recommend
trying to :django-admin:`routine import` your site log archive if you have one into our
containerized build to try out the SLM and identify any pain points. If you have to make
significant modifications or additions to behavior you will likely have to build out your
own manual installation, because our basic container includes only the default functionality
with basic toggles.

There are generally three deployment contexts under which you might wish to run an SLM.
Hereafter, we will use the following terminology to describe these deployments:

* **develop** - A deployment used for development. You might run this on a local server,
  but typically each developer will have their own local instance running on their
  own machine connected to their own database so they can experiment without interfering
  with other developers.
* **production** - This is your live instance of the SLM that is used for your real world
  data.
* **staging** - Depending on your operational requirements you may wish to run a staging
  server with an identical configuration and data to your production server to test out
  updates before deploying them to production.


.. _manual_install:

Manual Installation
===================

The SLM is both a :doc:`Django app <django:ref/applications>` and a fully deployable website. Many
users of the SLM will want to customize it significantly (things like adding
:pypi:`django-ldap` or :doc:`two-factor authentication <django-allauth:mfa/index>`). It can also
be deployed out of the box with a :ref:`minimal configuration <configuration>`. We recommend trying
a minimal development set up first to familiarize yourself with the software and identify any data
importing pain points. The following guide includes instructions for running the SLM out of the
box and for generating a scaffold to customize it. We will first work through a
:ref:`local develop <slm-startproject>` installation and then we cover
:ref:`deployment to a production server <deploy>`.

To facilitate customization we provide a bundled command slm-startproject_ to generate a scaffold to
build off of (not unlike Django's :django-admin:`startproject`). But first we must install some
dependencies.

Dependencies
############

Most of the dependencies will be the same between different deployments, but production will
require a web server and other production specific requirements. The following table lists
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
     - >=14
     - ✅
     - Relational Database (RDBMS)
   * - PostGIS_
     - >=3.4
     - ✅
     - Geographic information system extension to PostgreSQL_.
   * - Django_ & GeoDjango_
     - ==4.2.x
     - ✅
     - Django will be installed automatically, but GeoDjango_ has external dependencies that may
       need to be installed manually.
   * - uv_
     - >=0.7
     - ✅
     - A python build and package management system. Used by the SLM and by slm-startproject_
   * - pgAdmin_
     - >=9.0
     -
     - A graphical PostgreSQL management utility. Recommended for local development.

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

**If you are not customizing the SLM, skip ahead to step 2.**

To get up and running quickly with your customized SLM deployment we bundle a command called
slm-startproject_ that will scaffold out a directory structure and settings files for you to start
working with. Before running slm-startproject_ you will need to have installed all of GeoDjango_'s
dependencies as well as PostgreSQL_ and PostGIS_ and uv_. You do not need to install Django_
itself yet though.

(1) Run ``slm-startproject``
----------------------------

.. tabs::

  .. tab:: uvx

    uvx_ should be able to find our ``slm-startproject`` command. You can test this by running:

    .. code:: bash

      ?> uvx --from igs-slm --prerelease allow slm-startproject --help

  .. tab:: pip

    You can install the :pypi:`igs-slm` package into your local environment and run the command directly.

    .. code:: bash

      ?> pip install igs-slm
      ?> slm-startproject --help

  .. tab:: github

    You also have the option of working with our development version from github, but unless you
    have a compelling reason to do so you should use the release on pypi.

    .. code:: bash

      ?> git clone https://github.com/International-GNSS-Service/SLM.git
      ?> cd SLM
      ?> uv sync
      ?> uv run slm-startproject --help

you should see this:


.. typer:: slm.bin.startproject:app
    :prog: slm-starproject
    :theme: dark
    :width: 70
    :preferred: svg
    :convert-png: latex

|

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
    How should we connect to the database (db url)? [postgis:///{site}]: <enter>
    Install the mapbox map app? [Y/n]: <enter>
    Use IGS sitelog validation defaults? [Y/n]: <enter>

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


(2) Create environment & database
---------------------------------

.. tabs::

  .. tab:: Basic Install

    * Use either psql_ or pgAdmin_ to create a database called ``slm``.

    * We recommend creating a local development :mod:`python virtual environment <venv>`, but you
      may also use any python on your system that meets the :pypi:`igs-slm` minimum python
      requirement.

    * You will need to set a few environment variables and create an environment variable file so
      the SLM knows some basic things about itself.

    In your local development directory:

    .. code-block:: bash

      ?> python -m venv .venv
      ?> source .venv/bin/activate
      (.venv) ?> export SLM_ENV=`pwd`/.env
      (.venv) ?> touch .env
      (.venv) ?> pip install "igs-slm[debug]"

    Add a minimal configuration to the .env file. It may look something like this. You may also
    refer to the :ref:`configuration` page for all of the available settings. The most important
    settings are :setting:`SLM_ENV`, :setting:`BASE_DIR`:

    .. code-block:: bash

      DEBUG=True
      BASE_DIR=./
      SLM_ORG_NAME="ORG"
      SLM_SITE_NAME="localhost"
      # you may have to set these paths if your postgis libraries
      # are in non-standard locations
      # GEOS_LIBRARY_PATH=/path/to/libgeos_c.dylib
      # GDAL_LIBRARY_PATH=/path/to/libgdal.dylib


  .. tab:: Custom Install

    * Use either psql_ or pgAdmin_ to create the database that slm-startproject_ instructs you to.
      In our example this database would be named ``network``.

    * Use uv to install the virtual environment then activate it.

        .. code-block:: bash

          ?> cd ./network
          ?> uv sync --all-extras

.. _import_sitelogs:

(3) Import Existing Logs and Deploy
-----------------------------------

The SLM ships with a number of :ref:`pre-defined routines <routines>`. If you do not have any
existing logs to import you'll probably just want to run :django-admin:`routine deploy`.
Otherwise gather your logs into a single directory or tar file and run the
:django-admin:`routine install` routine:

.. tabs::

  .. tab:: Basic Install

    .. code-block:: bash

      (.venv) ?> slm routine install

  .. tab:: Custom Install

    .. code-block:: bash

      ?> uv run network routine install

You will be prompted to create a superuser account and also for a file path or directory containing
site logs you wish to import. After the import is finished an html log of the import process will
open.

The data import will both generate logs and record import errors and warnings as alerts and
validation flags in the database so you can manually go through the web interface and correct any
errors.

(4) Run the Development Server
------------------------------

You should now be able to start up the development server and see data in your SLM instance.

.. tabs::

  .. tab:: Basic Install

    .. code-block:: bash

      (.venv) ?> <slm> runserver
      Performing system checks...

      System check identified no issues (1 silenced).
      Django version 4.2.23, using settings 'slm.settings.root'
      Starting development server at http://127.0.0.1:8000/
      Quit the server with CONTROL-C.

  .. tab:: Custom Install

    .. code-block:: bash

      ?> uv run network runserver
      Performing system checks...

      System check identified no issues (1 silenced).
      Django version 4.2.23, using settings 'sites.network.develop'
      Starting development server at http://127.0.0.1:8000/
      Quit the server with CONTROL-C.

In addition to the front end interface where site logs are edited, moderated and published. We use
the `Django admin for a more direct access to system data <http://127.0.0.1:8000/admin>`_. This is
where we control permissions and make site adjustments. You may also add users and agencies and set
their permissions through the admin.


.. _deploy:

Deploy
######

.. warning::

  We offer a notional deployment strategy here. There are myriad operational concerns that will vary
  based on your organization's so the following examples are merely suggestions.

If you are customizing the SLM, the scaffold we generated should be checked into version control.
You can manage it just like you would a normal python package. It can be built and installed using
uv_ or pip_ or any other python package management tooling that supports wheels. When you install it
it will pull in all of its required python dependencies.

First you need to make sure your host server has all the dependencies installed, PostGIS_, etc.
Then you should use ``psql`` to create the database. It is usually sufficient to configure PostGIS_
for `peer authentication <https://www.postgresql.org/docs/current/auth-peer.html>`_ and give your
web server user all the appropriate permissions to the database.

User Permissions
----------------

You will likely want a dedicated non-login user to run the web server. Most package managers will
install your web server using this scheme. This user should share a group with the DevOps user -
which usually means adding your DevOps user to the www-data group or something similar. The SLM will
create directories with default 0o770 permissions and files with 0o660 permissions, so this should
work. Many other user/group combinations will also work. If you have this split scheme and are using
peer authentication, you will need to create another postgres user for your DevOps account with the
same privileges as your web server user.

.. tip::

  It is also a good idea to make sure the web server user cannot write to files in your python
  virtual environment.

Setup Node & esbuild
--------------------

Production deployments of the SLM require esbuild_ to bundle static javascript and css files. To
install esbuild_, your DevOps account will need an install of node_. You may want to use nvm_ to
do this:

.. code-block:: bash

  ?> curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  ?> source ~/.nvm/nvm.sh
  ?> nvm install --lts
  ?> npm install -g esbuild
  ?> esbuild --version


Setup Python
------------

Check that your system Python meets the :pypi:`igs-slm` minimum requirement, then create a virtual
environment somewhere you think is appropriate. For example:

.. code-block:: bash

  ?> python3 -m venv /opt/slm_venv

Build and Install
-----------------

.. tabs::

  .. tab:: Basic Install

    .. code-block:: bash

      ?> source /opt/slm_venv/bin/activate
      # install with gunicorn if using nginx or mod_wsgi if using Apache
      (slm_venv) ?> pip install igs-slm
      # if using nginx:
      (slm_venv) ?> pip install gunicorn
      # if using apache:
      (slm_venv) ?> pip install mod_wsgi

  .. tab:: Custom Install

    .. code-block:: bash

      # in your git repository holding your slm-startproject
      ?> uv build
      # get the wheel to your server somehow
      ?> scp dist/network-x.x.x-py3-none-any.whl yourserver:./
      ?> ssh yourserver
      ?> source /opt/slm_venv/bin/activate
      # install with gunicorn if using nginx or mod_wsgi if using Apache
      (slm_venv) ?> pip install network-x.x.x-py3-none-any.whl
      # if using nginx:
      (slm_venv) ?> pip install gunicorn
      # if using apache:
      (slm_venv) ?> pip install mod_wsgi

Filesystem
----------

We recommend setting up your site's working directory somewhere under /var/www:

.. tabs::

  .. tab:: Basic Install

    .. code-block:: bash

      ?> mkdir -p /var/www/network.example.com/production
      ?> cd /var/www/network.example.com/production
      ?> mkdir static media logs secrets

    You will need to create an environment file to tell the SLM about itself:

    .. code-block:: bash
      :caption: /var/www/network.example.com/production/.env

      DEBUG=False
      BASE_DIR=/var/www/network.example.com/production
      SLM_ORG_NAME="Example"
      SLM_SITE_NAME="network.example.com"

  .. tab:: Custom Install

  .. code-block:: bash

    ?> mkdir -p /var/www/network.example.com/production
    ?> cd /var/www/network.example.com/production
    ?> mkdir static media logs secrets

web servers
-----------

.. tabs::

  .. tab:: Nginx

    The recommended way to serve the SLM with Nginx_ is to proxy requests to a gunicorn_ instance
    running the SLM. Here's a notional Nginx_ configuration that will serve your SLM instance:

    .. code-block:: nginx

      # Redirect HTTP to HTTPS
      server {
          listen 80;
          server_name network.example.com;

          return 301 https://$host$request_uri;
      }

      # HTTPS server block
      server {
          listen 443 ssl;
          server_name network.example.com;

          # SSL Certificate and Key (adjust paths)
          ssl_certificate /etc/ssl/certs/fullchain.pem;
          ssl_certificate_key /etc/ssl/certs/privkey.pem;

          # (Optional) Strong security configuration
          ssl_protocols TLSv1.2 TLSv1.3;
          ssl_ciphers HIGH:!aNULL:!MD5;
          ssl_prefer_server_ciphers on;
          ssl_session_cache shared:SSL:10m;
          ssl_session_timeout 1d;
          ssl_session_tickets off;

          # (Optional) HSTS for extra security
          add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

          # Proxy to Gunicorn/Django app
          location / {
              proxy_pass http://127.0.0.1:8000;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $scheme;
          }

          # Static files
          location /static/ {
              alias /var/www/network.example.com/production/static/;
          }

          # Media files
          location /media/ {
              alias /var/www/network.example.com/production/media/;
          }
      }

    We recommend using a systemd service to run gunicorn_ in the background. Here's an example
    systemd service file:

    .. code-block:: ini

      [Unit]
      Description=Gunicorn instance to serve SLM
      After=network.target

      [Service]
      User=www-data
      Group=www-data
      WorkingDirectory=/var/www/network.example.com/production
      Environment="SLM_ENV=/var/www/network.example.com/production/.env"
      ExecStart=/opt/slm_venv/bin/gunicorn --workers 4 --bind unix:/var/www/network.example.com/production/slm.sock sites.network.production.wsgi:application

      [Install]
      WantedBy=multi-user.target


  .. tab:: Apache

    If you are using Apache_ you can use the :pypi:`mod_wsgi` module to run the SLM under Apache_.

    Here's a notional Apache_ virtual host configuration that will serve your SLM instance:

    .. code-block:: apache

      <VirtualHost *:443>
          ServerName network.example.com
          DocumentRoot /var/www/network.example.com/production

          # Enable SSL
          SSLEngine on
          SSLCertificateFile /etc/ssl/certs/fullchain.pem
          SSLCertificateKeyFile /etc/ssl/certs/privkey.pem
          # (Optional) Intermediate chain if needed
          # SSLCertificateChainFile /etc/ssl/certs/chain.pem

          # Hardened SSL settings
          SSLProtocol all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1
          SSLCipherSuite HIGH:!aNULL:!MD5
          SSLHonorCipherOrder on
          SSLCompression off
          SSLSessionTickets off

          # WSGI configuration
          WSGIDaemonProcess network python-home=/opt/slm_venv python-path=/var/www/network.example.com/production
          WSGIProcessGroup network

          WSGIEnvVar SLM_ENV /var/www/network.example.com/production/.env

          # TODO - For Basic Install:
          WSGIScriptAlias / /opt/slm_venv/lib/python3.x/site-packages/slm/wsgi.py

          # TODO - For Custom Install:
          WSGIScriptAlias / /opt/slm_venv/lib/python3.x/site-packages/sites/network/production/wsgi.py

          # Static & media files
          Alias /static/ /var/www/network.example.com/production/static/
          Alias /media/ /var/www/network.example.com/production/media/

          <Directory /var/www/network.example.com/production/static>
              Require all granted
          </Directory>

          <Directory /var/www/network.example.com/production/media>
              Require all granted
          </Directory>

          # Logging
          ErrorLog ${APACHE_LOG_DIR}/network_error.log
          CustomLog ${APACHE_LOG_DIR}/network_access.log combined
      </VirtualHost>


routine deploy
--------------

Anytime you install a new version of your SLM you need to run :django-admin:`routine deploy`. This
will migrate the database and bundle all static files:


.. tabs::

  .. tab:: Basic Install

    .. code-block:: bash

      (slm_venv) ?> slm routine deploy

    If it is the first installation you can run the :django-admin:`routine install` routine instead:

    .. code-block:: bash

      (slm_venv) ?> slm routine install

  .. tab:: Custom Install

    .. code-block:: bash

      (slm_venv) ?> network routine deploy

    If it is the first installation you can run the :django-admin:`routine install` routine instead:

    .. code-block:: bash

      (slm_venv) ?> network routine install


.. tip::

  Refer to :ref:`upgrading` for advice on updating the SLM.

.. _containerization:

Containerization
================

.. todo::

    Instructions for running our containers..


.. _fast_hosting:

Fast Hosting
============

.. todo::

    Instructions for quickly deploying to a hosting service..
