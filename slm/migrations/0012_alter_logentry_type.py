# Generated by Django 4.1.8 on 2023-04-27 23:30

import django_enum.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "0011_alter_siteidentification_fracture_spacing"),
    ]

    operations = [
        migrations.AlterField(
            model_name="logentry",
            name="type",
            field=django_enum.fields.EnumPositiveSmallIntegerField(
                choices=[
                    (1, "Site Proposed"),
                    (2, "Add"),
                    (3, "Update"),
                    (4, "Delete"),
                    (5, "Publish"),
                    (6, "Log Upload"),
                    (7, "Image Upload"),
                    (8, "Attachment Upload"),
                    (9, "Image Published"),
                    (10, "Attachment Published"),
                    (11, "Image Unpublished"),
                    (12, "Attachment Unpublished"),
                    (13, "Image Deleted"),
                    (14, "Attachment Deleted"),
                ],
                db_index=True,
            ),
        ),
    ]
