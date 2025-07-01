from pathlib import Path
from pprint import pformat

from django.db import migrations
from django.db.models import Count, Func, Q


def noop(apps, schema_editor):
    pass


def verify_index(apps, schema_editor):
    """
    Run final sanity check.

    Verifies the following conditions:

        1. All files exist
        2. All db row names match the file names
        3. No files are referenced by more than one db row
        4. That all file timestamps match the index begin timestamp
    """
    ArchivedSiteLog = apps.get_model("slm", "ArchivedSiteLog")

    assert ArchivedSiteLog.objects.filter(file__startswith="/").count() == 0, (
        "There are still absolute paths in the archived site log file field."
    )

    # final sanity checks
    # check that all files exist
    for archived in ArchivedSiteLog.objects.all():
        assert Path(archived.file.path).is_file(), (
            f"WARNING: {archived} index file does not exist!"
        )
        assert archived.name == Path(archived.file.name).name, (
            f"{Path(archived.file.name).name}/{archived.name} mismatch!"
        )

    # check that all files are unique
    duplicates = (
        ArchivedSiteLog.objects.values("file")  # file.name
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )

    # this must be true because following migrations will make this field unique!
    assert not duplicates.exists(), (
        f"Some indexes share the same files: {pformat(duplicates)}"
    )

    bad_timestamps = ArchivedSiteLog.objects.filter(
        ~Q(timestamp=Func("index__valid_range", function="lower"))
    )
    assert not bad_timestamps.count(), (
        f"Some indexes timestamps do not align with the valid range: {pformat(bad_timestamps)}"
    )


class Migration(migrations.Migration):
    dependencies = [
        # Replace with your latest migration
        ("slm", "simplify_index"),
    ]

    operations = [
        migrations.RunPython(verify_index, reverse_code=noop),
    ]
