.. include:: refs.rst

.. _changelog:

==========
Change Log
==========

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
