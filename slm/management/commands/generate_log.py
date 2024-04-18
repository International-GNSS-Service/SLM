import logging
from pathlib import Path

from django.core.management import BaseCommand, CommandError
from django.utils.translation import gettext as _

from slm.api.serializers import SiteLogSerializer
from slm.defines import SiteLogFormat
from slm.models import ArchiveIndex, Site


class Command(BaseCommand):
    help = (
        "Generate a site log in the specified format for the specified site "
        "and print it to stdout. Optionally pull the log from the archive or "
        "regenerate it based on given parameters."
    )

    logger = logging.getLogger(__name__ + ".Command")

    def add_arguments(self, parser):
        parser.add_argument(
            "site", metavar="S", nargs=1, help=_("The name of the site.")
        )

        parser.add_argument(
            "-f",
            "--format",
            dest="format",
            type=SiteLogFormat,
            default=SiteLogFormat.LEGACY,
            choices=[frmt.ext for frmt in SiteLogFormat],
            help=_("The format of the log. (Default: {})").format(
                SiteLogFormat.LEGACY.ext
            ),
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--head",
            dest="head",
            action="store_true",
            default=False,
            help=_("Generate the log from the head edits."),
        )
        group.add_argument(
            "--archive",
            dest="archive",
            action="store_true",
            default=False,
            help=_("Pull from archive rather than generating."),
        )

    def handle(self, *args, **options):
        try:
            site = Site.objects.get(name__istartswith=options["site"][0])

            if options["archive"]:
                index = ArchiveIndex.objects.filter(site=site).first()
                log_file = index.files.filter(log_format=options["format"]).first()
                if not log_file:
                    raise CommandError(
                        _(
                            "Latest index of {} does not have a log file of "
                            "format {}"
                        ).format(site.name, options["format"].ext)
                    )

                print(Path(log_file.file.path).read_text())
            else:
                print(
                    SiteLogSerializer(
                        instance=site, published=None if options["head"] else True
                    ).format(options["format"])
                )

        except Site.DoesNotExist:
            raise CommandError(
                _("Site of name {} does not exist.").format(options["site"][0])
            )
        except Site.MultipleObjectsReturned:
            raise CommandError(
                _("Multiple sites start with {} please be more specific.").format(
                    options["site"][0]
                )
            )
