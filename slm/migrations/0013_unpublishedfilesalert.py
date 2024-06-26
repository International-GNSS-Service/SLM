# Generated by Django 4.1.8 on 2023-04-28 07:03

import django.db.models.deletion
from django.db import migrations, models

import slm.models.alerts


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "0012_alter_logentry_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnpublishedFilesAlert",
            fields=[
                (
                    "alert_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="slm.alert",
                    ),
                ),
                (
                    "site",
                    models.OneToOneField(
                        blank=True,
                        default=None,
                        help_text="The site this alert applies to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unpublished_files_alert",
                        to="slm.site",
                    ),
                ),
            ],
            options={
                "verbose_name": "Unpublished Files",
                "verbose_name_plural": " Alerts: Unpublished Files",
                "unique_together": {("site",)},
            },
            bases=(slm.models.alerts.AutomatedAlertMixin, "slm.alert"),
        ),
    ]
