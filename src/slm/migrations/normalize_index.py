import os
from pathlib import Path

from django.db import migrations
from django.db.models import DateTimeField
from django.db.models.functions import Lower


def site_upload_path(instance, filename):
    """
    The historical site_upload_path implementation.
    """
    return f"archive/{instance.site.name}/{filename}"


def normalize_index(apps, schema_editor):
    from django.conf import settings

    ArchivedSiteLog = apps.get_model("slm", "ArchivedSiteLog")
    Site = apps.get_model("slm", "Site")

    # paths to update - we do this after the database updates succeed, so if they're rolled
    # back after an exception the disk state will still match the db
    path_changes = []
    unindexed = absolute = normalized = timestamps = 0

    for archived in ArchivedSiteLog.objects.filter(file__startswith="/"):
        current_name = Path(archived.file.name)
        # change to relative path
        archived.file.name = site_upload_path(archived, current_name.name)
        assert not archived.file.name.startswith("/")
        if not Path(archived.file.path).is_file():
            if current_name.is_file():
                raise RuntimeError(
                    f"Archived file {archived.file.name} does not exist at the new path: {Path(archived.file.path)}"
                )
            else:
                print(
                    f"WARNING: Archived file {archived.file.name} does not exist on disk!"
                )
        archived.name = Path(archived.file.name).name
        archived.save(update_fields=["file", "name"])
        absolute += 1
        # print(f"Fixed indexed file {current_name} -> {archived.file.name}")

    # remove unindexed files
    for site in Site.objects.all():
        site_dir = Path(settings.MEDIA_ROOT / "archive" / site.name)
        if not site_dir.is_dir():
            continue
        files = {site_dir / file for file in os.listdir(site_dir)}
        if ArchivedSiteLog.objects.filter(site=site).count() != len(files):
            for archived in ArchivedSiteLog.objects.filter(site=site):
                try:
                    files.remove(Path(archived.file.path))
                except KeyError as err:
                    raise RuntimeError() from err  # this should not happen
            for file in files:
                # print(f"WARNING: deleting unindexed {file} in archive!")
                unindexed += 1
                file.unlink()

    names = set()
    for archived in ArchivedSiteLog.objects.annotate(
        begin=Lower("index__valid_range", output_field=DateTimeField())
    ).all():
        current_path = Path(archived.file.path)
        new_path = Path(archived.file.path)
        update_fields = []

        if archived.timestamp != archived.begin:
            update_fields.append("timestamp")
            archived.timestamp = archived.begin
            timestamps += 1

        # make lowercase if necessary
        if not current_path.name.islower():
            new_path = current_path.with_name(current_path.name.lower())

        # convert nine to four char if necessary
        if (
            archived.log_format == 1
            and "_" in new_path.name
            and new_path.name.index("_") == 9
        ):
            new_path = new_path.with_name(f"{new_path.name[0:4]}{new_path.name[9:]}")
        # convert four char to nine if necessary
        elif (
            archived.log_format == 4
            and "_" in new_path.name
            and new_path.name.index("_") == 4
        ):
            new_path = new_path.with_name(
                f"{archived.index.site.name[0:9].lower()}{new_path.name[4:]}"
            )

        # add timestamp if necessary
        # collisions - can happen in weird 4char/9char inconsistent same date cases
        if new_path.name.count("_") == 2 or new_path.name in names:
            new_path = new_path.with_name(
                f"{new_path.stem[0 : new_path.stem.rindex('_')]}_{archived.index.valid_range.lower.strftime('%H%M%S')}{new_path.suffix}"
            )

        if new_path != current_path:
            normalized += 1
            path_changes.append((current_path, new_path))
            names.add(new_path.name)
            archived.file.name = archived.file.name.replace(
                current_path.name, new_path.name
            )
            archived.name = Path(archived.file.name).name
            update_fields.extend(["file", "name"])
            # print(f"Normalized indexed file name {current_path.name} -> {new_path.name}")
        else:
            names.add(current_path.name)

        if update_fields:
            archived.save(update_fields=update_fields)

    for old, new in path_changes:
        if (
            new.is_file()
            and not (new.name == old.name.lower())
            and new.read_text() != old.read_text()
        ):
            print(f"WARNING: {old} will overwrite {new}!")
        old.rename(new)

    print(f"\nConverted {absolute} absolute paths to relative paths.")
    print(f"Deleted {unindexed} files.")
    print(f"Normalized {normalized} files.")
    print(f"Synchronized {timestamps} file timestamps.")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        # Replace with your latest migration
        ("slm", "add_index_order_index"),
    ]

    operations = [
        migrations.RunPython(normalize_index, reverse_code=noop, atomic=True),
    ]
