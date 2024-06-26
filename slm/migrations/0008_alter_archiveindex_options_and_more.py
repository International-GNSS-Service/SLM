# Generated by Django 4.1.7 on 2023-04-05 04:06

import django.core.validators
from django.db import migrations, models

import slm.models.sitelog


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "0007_alter_dataavailability_rate"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="archiveindex",
            options={
                "ordering": ("-begin",),
                "verbose_name": "Archive Index",
                "verbose_name_plural": "Archive Index",
            },
        ),
        migrations.AlterUniqueTogether(
            name="archiveindex",
            unique_together={("site", "begin")},
        ),
        migrations.AlterUniqueTogether(
            name="logentry",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="archiveindex",
            name="begin",
            field=models.DateTimeField(
                db_index=True,
                help_text="The point in time at which this archive became valid.",
            ),
        ),
        migrations.AlterField(
            model_name="archiveindex",
            name="end",
            field=models.DateTimeField(
                db_index=True,
                help_text="The point in time at which this archive stops being valid.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="siteform",
            name="date_prepared",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="Enter the date the site log was prepared (CCYY-MM-DD).",
                null=True,
                validators=[
                    django.core.validators.MaxValueValidator(
                        slm.models.sitelog.utc_now_date
                    )
                ],
                verbose_name="Date Prepared",
            ),
        ),
    ]
