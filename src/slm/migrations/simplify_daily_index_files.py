"""
If multiple index files exist for a given station on a given day we remove the timestamp
from the name of the latest daily file and add the timestamp to the earliest daily file.
"""

from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from django.db import migrations
from django.db.models import Count, Value
from django.db.models.functions import Length, Replace


def simplify_index(apps, schema_editor):
    ArchivedSiteLog = apps.get_model("slm", "ArchivedSiteLog")
    ArchiveIndex = apps.get_model("slm", "ArchiveIndex")

    multi_day_indexes = ArchiveIndex.objects.filter(
        files__in=ArchivedSiteLog.objects.annotate(
            ucount=Length("file") - Length(Replace("file", Value("_"), Value("")))
        ).filter(ucount__gte=2)
    ).distinct()

    multi_day_tuples = list(
        multi_day_indexes.extra(select={"range_date": "DATE(lower(valid_range))"})
        .values("site__name", "range_date")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .values_list("site__name", "range_date", flat=False)
    )

    for station, day in multi_day_tuples:
        lower = datetime.combine(day, time.min, tzinfo=timezone.utc)
        upper = lower + timedelta(days=1)
        indexes = ArchiveIndex.objects.filter(
            site__name=station,
            valid_range__startswith__gte=lower,
            valid_range__startswith__lte=upper,
        ).order_by("valid_range")
        assert indexes.count() >= 2
        first = indexes.first()
        last = indexes.last()

        for file in first.files.all():
            current_path = Path(file.file.path)
            new_path = Path(file.file.path)
            if current_path.stem.count("_") < 2:
                new_path = current_path.with_name(
                    f"{current_path.stem}_{first.valid_range.lower.strftime('%H%M%S')}{current_path.suffix}"
                )
                file.file.name = file.file.name.replace(
                    current_path.name, new_path.name
                )
                file.name = Path(file.file.name).name
                current_path.rename(new_path)
                file.save(update_fields=["file", "name"])
                print(f"Updated {current_path.name} -> {new_path.name}")

        for file in last.files.all():
            current_path = Path(file.file.path)
            new_path = Path(file.file.path)
            if current_path.stem.count("_") >= 2:
                new_path = current_path.with_name(
                    "_".join(current_path.stem.split("_")[:-1]) + current_path.suffix
                )
                file.file.name = file.file.name.replace(
                    current_path.name, new_path.name
                )
                file.name = Path(file.file.name).name
                current_path.rename(new_path)
                file.save(update_fields=["file", "name"])
                print(f"Updated {current_path.name} -> {new_path.name}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "0005_slmversion"),
    ]

    operations = [
        migrations.RunPython(simplify_index, reverse_code=noop, atomic=True),
    ]
