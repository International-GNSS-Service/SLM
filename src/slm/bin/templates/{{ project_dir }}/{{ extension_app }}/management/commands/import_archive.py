"""
Django has administrative management commands that are run in the boostrapped Django environment.
That means - with a live connection to the database and all of the Django internals loaded so
you may interface with the data via the ORM just as you do in request handling code.

The SLM provides a number of commands out of the box that do various common administrative tasks.
This command imports a sitelog file index from a given directory or tar file. It will be run
usually once at the beginning of your SLM deployment to import your current data. After that
data updates will be done by users through the web UI.

In Django, management commands can be overridden by apps futher up the app stack from the command's
original definition. We do that here with import_archive. We inherit from the SLM command and
stub out the process_filename hook. The default behavior will most likely suffice for your
deployment, but if your legacy data filenames differ from what is expected from the base
import_archive command you can handle that here. You may also delete this file if the default
implementation works for you. We provide this here as an example of extending an SLM defined
management command.

Management commands: https://docs.djangoproject.com/en/stable/howto/custom-management-commands/

We use django-typer to add extra goodies like typer hint CLI definitions and shell tab completion
support: https://django-typer.readthedocs.io/en/latest/

# todo slm management commands link
"""

import typing as t
from slm.management.commands.import_archive import (
    Command as ImportArchive,
    FileMeta
)



class Command(ImportArchive):

    def process_filename(
        self, filename: str, site_name: str = "", mtime: t.Optional[int] = None
    ) -> t.Optional[FileMeta]:
        """
        The base class calls this hook to process a filename. This method should return
        a FileMeta object or None if this file is not a log file and/or uninterpretable
        as a log file.

        .. note::
            We provide a hook here as an example of 

        :param filename: The name of the file, including the extension.
        :param site_name: A string that might possibly be the site name and could
            be used if no site name is determinable from the filename.
        :return FileMeta or None if the filename was not interpretable
        """
        meta = super().process_filename(filename, site_name, mtime)
        # todo - handle your special case!
        # if meta is None:
        #     return FileMeta(
        #         filename=filename,
        #         name=site_name,
        #         mtime=mtime,
        #         format=?,
        #         file_date=?,
        #         no_day=?,
        #     )
        return meta
