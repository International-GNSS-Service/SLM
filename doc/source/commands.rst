.. _ref-commands:

========
Commands
========

.. _routine:

routine
------------

.. automodule:: slm.management.commands.routine

Usage
~~~~~

.. argparse::
    :module: slm.management.commands.routine
    :func: get_parser
    :prog: manage.py

Example
~~~~~~~

To run all configured deploy routines:

.. code::

    $ manage.py routine deploy
