.. include:: refs.rst


=============
Configuration
=============

SLM is built on Django_ and as such all of the :doc:`configuration directives<django:ref/settings>`
available on Django_ and on the application stack that comprises SLM core are available. SLM
provides additional directives referenced here to customize its behavior and operational
configuration.

Django_ configuration directives are defined in a settings file. You should first familiarize
youself with how :doc:`Django configuration works <django:topics/settings>`. A Django configuration
file is simply a python file where configuration directives are python variables of any type
defined in all caps. The python import path to this configuration file must appear in the
``DJANGO_SETTINGS_MODULE`` environment variable. After Django_ is bootstrapped you can access a
configuration directive like so:

.. code-block:: python

    from django.conf import settings

    settings.DIRECTIVE_NAME


The SLM uses a third party extension, :doc:`django-split-settings <django-split-settings:index>` to
allow settings files to be composed across multiple files. The SLM defines many settings for you
which you should include in your settings file using the :func:`split_settings.tools.include`
function in combination with :func:`slm.settings.resource`.

We highly recommend using :ref:`slm-startproject <slm-startproject>` to scaffold out your project
and its settings files. Even if you do not ultimately use our recommended configuration, seeing how
we lay out configuration files may be of some help. A notional production SLM settings file might
look like this:

.. code-block:: python

    from split_settings.tools import include
    from slm.settings import resource, get_setting
    from pathlib import Path
    import getpass


    WSGI_APPLICATION = "include.path.to.your.wsgi.application"

    DEBUG = False  # never run DEBUG mode in production!
    SITE_DIR = Path("/var/www/path/to/your/site/directory")
    BASE_DIR = SITE_DIR

    # Should be the scheme-less url
    SLM_SITE_NAME = "slm.yourdomain.org"
    SLM_ORG_NAME = "Your Organization"

    # https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts
    ALLOWED_HOSTS = [
        SLM_SITE_NAME,
        # in some production configurations you may need to add your server's ip address
        # to this list
    ]

    # https://docs.djangoproject.com/en/stable/ref/settings/#media-root 
    MEDIA_ROOT = SITE_DIR / 'media'

    # https://docs.djangoproject.com/en/stable/ref/settings/#static-root
    STATIC_ROOT = SITE_DIR / 'static'

    # This section deals with database connection. Alterations may need to be made for
    # deployment. We recommend running a database locally and using postgres user
    # authentication and disallowing any non-local connections. This means your database
    # is as secure as the system user running your SLM deployment.
    # 
    # You may of course, use any number of database settings or have multiple databases:
    # https://docs.djangoproject.com/en/stable/ref/databases/
    #
    # The directive below is the default DATABASES configuration for SLM
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'slm',
            'USER': getpass.getuser(),  # if postgres is configured for user authentication
            'ATOMIC_REQUESTS': True
        },
    }

    # The SLM uses geodjango. Unless gdal and geos are in standard locations on your production
    # server you will have to set their paths explicitly here:
    # https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/geolibs/
    # TODO
    # GDAL_LIBRARY_PATH = "/path/to/libgdal.so"
    # GEOS_LIBRARY_PATH = '/path/to/libgeos_c.so.1'

    # Make sure debug toolbar is not run in production - it can expose secrets!
    DJANGO_DEBUG_TOOLBAR = False

    # bring in the SLM configuration directives here
    include(resource("slm.settings", "root.py"))
    # if you want to use IGS's default validation rules include our validation settings
    # include(resource("slm.settings", "validation.py"))

    # If you want to install additional apps, or customize the INSTALLED_APPS defined
    # by the SLM root config you can do so like this
    INSTALLED_APPS = [
        # add more apps here
        get_setting("INSTALLED_APPS")  # bring in all of the SLM defined apps
        # or here
    ]

    ROOT_URLCONF = "import.path.to.your.urls"

    # ADMINS will receive email notifications when exceptions are encountered or 500 errors
    # returned to user requests
    ADMINS = [
        #("Your Name", "Email Address")
    ]

    # Change this setting if you would like the links serialized into site logs or geodesyml
    # files to use a different domain than the one of this SLM deployment.
    # For example, IGS's SLM is running on https://slm.igs.org but our public facing downloads
    # are from https://network.igs.org
    # SLM_FILE_DOMAIN = 'https://files.yourdomain.org'


Settings
========

.. setting:: SLM_SITE_NAME

``SLM_SITE_NAME``
------------------

    The domain name of your site without the scheme. e.g. "slm.igs.org"


.. setting:: SLM_STATION_NAME_REGEX

``SLM_STATION_NAME_REGEX``
------------------------

Provide a regular expression to validate new station names against. By
default no validation occurs and station names may be any string up to
50 characters in length.

For example the IGS station name standard uses this regular expression: 

.. code-block:: python
    
    SLM_STATION_NAME_REGEX = r"[\w]{4}[\d]{2}[\w]{3}"


.. setting:: SLM_STATION_NAME_HELP

``SLM_STATION_NAME_HELP``
------------------------

Override the help text used for station name field.
