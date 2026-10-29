.. include:: refs.rst

.. _changelog:

==========
Change Log
==========

v0.6.0b0 (2026-10-29)
=====================

* BREAKING: Drop support for Python < 3.11 and Django 4.2. Support Python 3.11-3.15 and
  Django 5.2 LTS.
* Upgrade dependencies, including django-typer 4, django-enum 2, enum-properties 2 and lxml 6.
* Add database check constraints for enumeration fields (django-enum 2).
* BREAKING: Migrations have been remade from the 0.5.0b0 version waypoint. Databases must be
  migrated by 0.5.0b0 before upgrading. See :ref:`version_waypoints` for the effect on apps
  that extend the SLM.
* :django-admin:`migrate` now checks for version waypoints before loading the migrations, so
  unsafe upgrades fail with a clear message.
* Station names are now always validated to exclude path separators, dots, whitespace and
  control characters, independent of :setting:`SLM_STATION_NAME_REGEX`, because they are
  used as file system path components and URL segments.
* Fix a reflected cross-site scripting issue in the site file upload API: the 404 and 403
  responses echoed the site name from the URL as HTML. They are now JSON ``detail`` errors
  like the rest of the API.
* Harden the front end against markup injection: autocomplete suggestions, table column
  filter options, time picker values, new site form errors and the edit page section
  targets are now HTML escaped or inserted as text. Autocomplete highlighting also no longer
  breaks on search terms containing regular expression metacharacters.
* The site file collision check now asks the file field's storage backend whether the
  destination exists instead of probing ``MEDIA_ROOT`` directly, so it honors the configured
  storage and refuses any path that escapes the storage root.
* Glob backed file views (``FileSystemDirectory``) now confine listings to the wildcard free
  root of the configured pattern, skipping symlinks that resolve outside of it, and reject
  relative patterns at startup. Serving a listed file, JSON listings and the ``match`` query
  parameter filter were broken for these views and now work. The ``match`` filter on archive
  listings mangled patterns beginning with ``s`` or ending with ``Z`` and failed outright on
  Python 3.14; it is now translated correctly.


v0.5.0b0 (2026-10-15)
=====================

.. important::

    This release is a :ref:`version waypoint <version_waypoints>`. Upgrades from earlier
    versions to versions after 0.5.0b0 must first upgrade to and migrate with 0.5.0b0.

* Fixed version waypoint checks: databases at a waypoint were refused upgrades past it,
  fresh databases were refused migrations once a waypoint existed, downgrades back to a
  waypoint were allowed and a stale cached database version could be used.
* Fixed `Thumbnail generation and retrieve is broken. <https://github.com/International-GNSS-Service/SLM/issues/214>`_
* Fixed `slm javascript is not loaded on DRF admin pages. <https://github.com/International-GNSS-Service/SLM/issues/209>`_
* Implemented `Allow admins to edit indexed site log files directly through the admin. <https://github.com/International-GNSS-Service/SLM/issues/207>`_
* Fixed `Downloads of site logs trigger generation of new formats for FORMER stations. <https://github.com/International-GNSS-Service/SLM/issues/203>`_
* Fixed `Site log download without a format suffix returns 500 <https://github.com/International-GNSS-Service/SLM/issues/230>`_
* Fixed `name_len query parameter on site log downloads returns 500 <https://github.com/International-GNSS-Service/SLM/issues/231>`_
* Fixed `Filtering alerts by user (?user=) returns 500 <https://github.com/International-GNSS-Service/SLM/issues/233>`_
* Fixed `Legacy parser silently accepts impossible dates <https://github.com/International-GNSS-Service/SLM/issues/236>`_
* Fixed `Login page throws a JavaScript error from Bootstrap tooltip/popover init <https://github.com/International-GNSS-Service/SLM/issues/237>`_
* Fixed section edits through the edit API not checking that the user may edit the site.
* Fixed archived site log file naming so that existing files are never overwritten.
* :django-admin:`validate_db` now validates any sites given explicitly, regardless of status.
* :django-admin:`generate_sinex` no longer includes proposed stations when
  ``--include-former`` is given.
* Removed IGS specific components from :django-admin:`generate_sinex` and the login page
  (part of `Separate out erroneous IGS specific references. <https://github.com/International-GNSS-Service/SLM/issues/198>`_).
* Added smoke and Playwright end-to-end test suites.


v0.4.1b0 (2025-11-10)
=====================

* Fixed `Sort all admin tables by default. <https://github.com/International-GNSS-Service/SLM/issues/197>`_

v0.4.0b0 (2025-11-07)
=====================

* Fixed `Publish Changes button shows for non-moderator users after form save. <https://github.com/International-GNSS-Service/SLM/issues/196>`_
* Fixed `Normal users cannot see some field flags. <https://github.com/International-GNSS-Service/SLM/issues/195>`_
* Fixed `Non super users cannot revert section changes - returns 403 <https://github.com/International-GNSS-Service/SLM/issues/193>`_
* Implemented `Add admin ability to impersonate a user. <https://github.com/International-GNSS-Service/SLM/issues/194>`_
* Fixed `Asset compression should not pull in esbuild latest at runtime <https://github.com/International-GNSS-Service/SLM/issues/190>`_


v0.3.0b0 (2025-10-24)
=====================

* Fixed `Cache clearing signal receivers are not registered. <https://github.com/International-GNSS-Service/SLM/issues/189>`_
* Implemented `filew_views should support entries that create listings without adding urls <https://github.com/International-GNSS-Service/SLM/issues/188>`_


v0.2.0b3 (2025-10-23)
=====================

* Fix issues with check_upgrade so that it fails gracefully when the version table is not present.
* Implemented `Should be able to pass string arguments to GeneratedFile views. <https://github.com/International-GNSS-Service/SLM/issues/184>`_
* Fixed `ArchivedLog view can erroneously include logs from last index date if multiple indexes exist for that date. <https://github.com/International-GNSS-Service/SLM/issues/183>`_
* Fixed `Need to be able to pass url kwargs to file view Entries. <https://github.com/International-GNSS-Service/SLM/issues/182>`_
* Fixed `LogEntry admin search field errors out <https://github.com/International-GNSS-Service/SLM/issues/181>`_
* Fixed `Add a validator to check XYZ/LLH consistency. <https://github.com/International-GNSS-Service/SLM/issues/180>`_
* Fixed `Generated SINEX with latitudes at 0 degrees S lose the sign <https://github.com/International-GNSS-Service/SLM/issues/176>`_
* Fixed `SLM site log serialization cuts lines at 79 characters - this should be 80. <https://github.com/International-GNSS-Service/SLM/issues/166>`_
* Fixed `Allow "URL for More Information" to split a url across multiple lines. <https://github.com/International-GNSS-Service/SLM/issues/165>`_
* Implemented `Antenna Alignment from True north should be desired not required. <https://github.com/International-GNSS-Service/SLM/issues/164>`_
* Fixed `Some malformed query parameters result in unhandled exceptions producing 500s instead of 400s <https://github.com/International-GNSS-Service/SLM/issues/162>`_
* Implemented `Provide app that contains the igs file list views. <https://github.com/International-GNSS-Service/SLM/issues/108>`_


v0.1.5b3 (2025-07-25)
=====================

* Fixed `WSGI_APPLICATION default is wrong <https://github.com/International-GNSS-Service/SLM/issues/154>`_
* Fixed `Provide SLM IGS station naming validation toggle. <https://github.com/International-GNSS-Service/SLM/issues/153>`_
* Fixed `Sometimes the javascript diffing/site log error renderer inserts extra newlines. <https://github.com/International-GNSS-Service/SLM/issues/151>`_


v0.1.5b2 (2025-07-15)
=====================

* Beta Bug Fix
* Added `Add debug dependency group <https://github.com/International-GNSS-Service/SLM/issues/155>`_
* Fixed `WSGI_APPLICATION default is wrong <https://github.com/International-GNSS-Service/SLM/issues/154>`_

v0.1.5b1 (2025-07-15)
=====================

* Beta Bug Fix
* Fixed `SLM_INCLUDE url inclusion is not working to spec <https://github.com/International-GNSS-Service/SLM/issues/152>`_

v0.1.5b0 (2025-07-15)
=====================

* Beta Increment
* Implemented `Allow environment variables to override specific default settings. <https://github.com/International-GNSS-Service/SLM/issues/150>`_
* Fixed `Empty sections on site log upload are not updated. <https://github.com/International-GNSS-Service/SLM/issues/149>`_
* Implemented `Make sure SINEX is ascii only, no-multi byte characters <https://github.com/International-GNSS-Service/SLM/issues/148>`_
* Implemented `Normalize archive index file names. <https://github.com/International-GNSS-Service/SLM/issues/147>`_
* Fixed `Some archivedsitelogs in the index have file names that are absolute paths. <https://github.com/International-GNSS-Service/SLM/issues/143>`_
* Implemented `Move site name database constraints to pluggable validation <https://github.com/International-GNSS-Service/SLM/issues/142>`_
* Fixed `Some site's final entry in the index has an end date attached. <https://github.com/International-GNSS-Service/SLM/issues/125>`_
* Implemented `Move from poetry to uv <https://github.com/International-GNSS-Service/SLM/issues/121>`_
* Implemented `Need new drop down option for Antenna Features Drop Down List <https://github.com/International-GNSS-Service/SLM/issues/118>`_
* Fixed `was not able to update section 12 for last INEG00MEX site log update <https://github.com/International-GNSS-Service/SLM/issues/117>`_
* Implemented `list of manufacturers not available at https://network.igs.org/api/public/ <https://github.com/International-GNSS-Service/SLM/issues/115>`_
* Implemented `Support safe upgrades. <https://github.com/International-GNSS-Service/SLM/issues/114>`_
* Fixed `Reverting a sitelog from UPDATED -> PUBLISHED creates an entry in the index because the published signal is triggered. <https://github.com/International-GNSS-Service/SLM/issues/112>`_
* Implemented `Javascript/css versioning & compression enhancement <https://github.com/International-GNSS-Service/SLM/issues/83>`_

v0.1.4b (2024-07-19)
====================

* Beta Increment

v0.1.2b (2024-07-18)
====================

* Beta increment

v0.1.1b (2024-07-18)
====================

* Beta increment

v0.1.0b (2024-07-17)
====================

* Initial Release (Beta)
