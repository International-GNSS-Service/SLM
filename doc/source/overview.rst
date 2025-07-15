.. include:: refs.rst

.. _overview:

========
Overview
========

History
=======

GNSS ground station networks have been in operation since the early 1990s. The information
technology challenges of managing these networks are manifest and the standards and practices for
doing so have evolved concurrently with the information technology field. The IGS_ first
standardized the `site log format <https://files.igs.org/pub/station/general/sitelog_instr_v2.0.txt>`_
in 1997 before the first XML standard was released in 1998. The needs of GNSS have often been on
the forefront of information technology and have necessitated the development of custom standards
and formats before modern and more widely used technologies were available.

The IGS_ has released this `Site Log Manager (SLM) software <https://github.com/International-GNSS-Service/SLM>`_
under the permissive open source `MIT License <https://opensource.org/license/mit>`_ in the hopes
that it will increase the fidelity of ground station meta data, ease the adoption of modern
technologies while supporting the three decades of legacy systems in current operation, and foster
a community of collaborative development and shared resources for ground station management.


Challenges
==========

The ultimate goal of a Site Log Manager is to maintain high fidelity, relevant and timely
information about a ground station network and make that information available to both human
operators and machine automations. There are many challenges to these objectives. To name a few:


* **Networks Are Managed By People**

  And people make mistakes. An SLM must be robust to the myriad kinds of mistakes people
  make: typos, mistranscriptions, misunderstandings, forgetfulness and tardiness.


* **Multiple Sources of Truth**

  Often the same information may exist in more than one place. There may be multiple
  different site logs that disagree about a receiver or which source do you trust when
  RINEX headers and a site log disagree?


* **Evolving Technologies**

  GNSS technologies are constantly evolving. So the pertinent information that organizations
  and researches are interested in does too. The data tracked for ground stations must be
  allowed to evolve over time, while maintaining backwards compatibility with older
  schemas/data models.


* **Legacy Systems**

  A significant amount of resources have gone into developing the legacy systems in operation
  around the world since the advent of GPS. These systems must be supported while
  simultaneously enabling modern systems to be built on new technologies.

* **Many Consumers**

  There are many different consumers of GNSS ground station data. Many are human some are
  not. An SLM must provide easy, reliable and normalized access to all consumers and
  applications.

* **Different Requirements**

  Many networks have their own idiosyncratic qualities and institutional requirements that
  may produce conflicts in what is expected to be present in station meta information.

Solutions
=========

To answer these challenges we have made some architectural decisions about the basic functionality
of the SLM.

Built on Django
---------------

The SLM is a dynamic website driven by a relational database on the backend. We did not reinvent
this wheel. The SLM is built on the Django_ web framework which is one of the most stable, highly
regarded and longest running open source web framework projects. This also means that the SLM is
written in Python_, one of the most
`widely used programming languages <https://www.tiobe.com/tiobe-index/>`_ in the world, meaning
that it can take advantage of the enormous corpus of freely licensed software available on the
`Python Package Index <https://pypi.org/>`_.


Lenient Data Model
------------------

The gold source of truth in a ground station network managed by an SLM should be in the SLM's
database. We refer to the fields that make up a canonical site log as the "data model". In the SLM,
this data model has been mapped to the tables and columns of a Relational Database Management
System (RDBMS_). Information may be serialized into site logs of various schemas and formats from
this database, but these should be considered copies and copies can become stale.

To facilitate backwards compatibility most fields in the data model are nullable
(meaning the database does not require them to exist).


Time-based Serialized Site Log Index
------------------------------------

The data model will change with time and the past is important. To facilitate backwards
compatibility with legacy data that may even predate the standardization of the site log format,
the SLM maintains a time based index of serialized site logs. This just means that the SLM stores
site logs on the file system and keeps entries in database that associates these files with the
time range during which they were valid. This ensures that the data model can change, and even lose
fields in time, but SLM managed networks will never lose information and maintain 100% traceability
into the past.


Validation
----------

Validation of site log data is mostly done in code by the SLM - we do not rely on many database
constraints. This enables our validation logic to be configurable. Different ground station
networks may have different requirements about which information must be recorded or how that
information is validated. The SLM provides reasonable IGS defaults, but allows customization.


Moderation
----------

Some networks, including the IGS network, are maintained by many different organizations and
personnel. The SLM provides a permission system that allows moderation before site log meta
information is released to external systems. This allows operators to determine where trust
lies in their network and empower it to control information while distributing labor as
broadly as possible.


Extensibility
-------------

The SLM is built on Django_ and Django_ provides a scaffold to build extensible software
components. It is possible to override or extend most parts of the SLM software including
HTML templates and even the data model itself. This means it is not a good idea to
`fork <https://en.wikipedia.org/wiki/Fork_(software_development)>`_ the SLM, but rather layer
your own extensions on top of it. If your team is considering forking the SLM, please reach
out to us or `open an issue <https://github.com/International-GNSS-Service/SLM/issues>`_
explaining what extension points you need to avoid a fork or better yet,
`open a PR <https://github.com/International-GNSS-Service/SLM/blob/main/CONTRIBUTING.md>`_.


APIs
----

To facilitate machine consumers the SLM provides several
`RESTful APIs <https://en.wikipedia.org/wiki/REST>`_ that provide well structured, queryable
JSON data structures containing site log meta information. These APIs sit between the consumer
and the data model and may evolve over time to accommodate new automated use cases.
