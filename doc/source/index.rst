.. include:: refs.rst

============
Introduction
============

The Site Log Manager (SLM) is a web framework for managing GNSS_ ground station meta data. The SLM
is maintained by the `International GNSS Service <https://igs.org>`_ and is freely licensed for
general use under the `MIT License <https://opensource.org/license/mit>`_. The SLM is implemented
in Python_ and JavaScript using the Django_ web framework.

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

This documentation speaks to multiple audiences:

* **Developers** will want to refer to the :ref:`installation`, :ref:`architecture`,
  :ref:`commands` and :ref:`reference` sections.
* **System administrators** may be interested in :ref:`configuration`, :ref:`upgrading` and
  :ref:`commands`.
* **Users** and **network coordinators** will be interested in the :ref:`user_manual`.
* **Developers** wishing to work with SLM managed data will be interested in the :ref:`api`.
* **Everyone**, but particularly **program managers** will want to take a look at the
  :ref:`overview`.

.. warning::

   The SLM has reached beta-maturity but is still undergoing significant organizational changes.
   Check back soon for new documentation and updates. A version 1.0 stable release is expected
   in 2026.

Please use the discussions_ page for general inquiry and the issues_ page to report bugs. Our road
map is on the projects_ page.

Contributions_ from the community are encouraged!



.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   installation
   upgrading
   configuration
   architecture/index
   manual/index
   commands
   dependencies
   APIs
   reference/index
   changelog

