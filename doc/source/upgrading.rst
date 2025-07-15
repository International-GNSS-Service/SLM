.. include:: refs.rst

.. _upgrading:

=========
Upgrading
=========

.. warning::

   Upgrades (e.g. running :django-admin:`migrate` or :django-admin:`routine deploy`) with a
   new version of igs-slm_ installed may cause hard or impossible to reverse changes to your
   data.

If you are using the SLM without extensions or with extensions without forking it, upgrading to
new versions of the igs-slm_ package is usually as straight forward as installing the latest
version and running :django-admin:`routine deploy`. This will run a collection of routines that
migrates the current database structure and state into alignment with the updated code. These
migration routines may alter database structure, database content or files on disk.

.. _always_backup:

Always Backup!
==============

Before upgrading to a new version of the igs-slm_ package ALWAYS backup the current state of
your SLM. The main state includes:

* The database(s).
* Files on disk - station images and attachments and the archive index.
* The software stack (``pip freeze``).

**If you have extended the igs-slm package with templates or code** that customizes or adds
additional functionality you will want to check the :ref:`changelog` to see if there are any
non-backwards compatible changes that require updates to your code. Even if there are none
the upgrade process may break some functionality. It is always recommended to backup all
of the state of your system before upgrading so rolling back is easy.

.. _version_waypoints:

Version Waypoints
=================

**The igs-slm package has version waypoints that upgrades must pass through**. Django
automatically generates migration files as the database models change. The igs-slm_
developers also create migrations to manipulate data and files. Over time these migration
files pile up and slow down testing and fresh installations. Django provides a
:django-admin:`squashmigrations` command to alleviate this problem, but it has significant
limitations. To get around these limitations we occasionally use a process similar to
`django-remake-migrations <https://browniebroke.com/blog/2025-03-03-introducing-django-remake-migrations/>`_
to eliminate old migration routines. Each time we do this we create a version waypoint that
upgrades must pass through. For instance if you are on version 0.1.4b and we have a version
waypoint at 0.1.5b, you will first need to upgrade to version 0.1.5b before you can upgrade
to version 0.1.6b.

Before a database migration is attempted, either as part of a :django-admin:`routine deploy`
or a :django-admin:`migrate` the SLM will check that the upgrade is safe and passes through
no waypoints. If it is not safe it will safely exit with a warning. You may also manually
check if your upgrade is safe by calling the :django-admin:`check_upgrade` command.

.. _semver:

Semantic Versioning
===================

The igs-slm_ package uses `semantic versioning <https://semver.org/>`_. Major non-backwards
compatible changes will bump the major version after the 1.0.0 release. It is important to note,
that semver allows breaking changes between the feature versions of the 0.x series. Do not expect
backwards compatibility between 0.x versions.
