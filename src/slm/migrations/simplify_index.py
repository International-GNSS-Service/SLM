from pathlib import Path

from django.db import migrations


def noop(apps, schema_editor):
    pass


def simplify_files(apps, schema_editor):
    ArchivedSiteLog = apps.get_model("slm", "ArchivedSiteLog")

    # paths to update - we do this after the database updates succeed, so if they're rolled
    # back after an exception the disk state will still match the db
    path_changes = []
    simplified = 0

    for archived in ArchivedSiteLog.objects.order_by("timestamp"):
        if archived.file.name.count("_") == 2:
            # make sure the first on a date does not have the timestamp on the end of it
            current_path = Path(archived.file.path)
            stem, ext = current_path.stem, current_path.suffix
            simple_path = current_path.with_name(f"{stem[: stem.rindex('_')]}{ext}")
            if not simple_path.exists():
                path_changes.append((current_path, simple_path))
                archived.file.name = archived.file.name.replace(
                    current_path.name, simple_path.name
                )
                archived.name = Path(archived.file.name).name
                archived.save(update_fields=["file", "name"])
                # print(f"Simplified indexed file name {current_path.name} -> {simple_path.name}")
                simplified += 1

    for old, new in path_changes:
        old.rename(new)

    print(f"\nSimplified {simplified} files.")


class Migration(migrations.Migration):
    dependencies = [
        # Replace with your latest migration
        ("slm", "normalize_index"),
    ]

    operations = [
        migrations.RunPython(simplify_files, reverse_code=noop, atomic=True),
    ]
