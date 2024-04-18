# Generated by Django 4.1.7 on 2023-04-06 06:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "0008_alter_archiveindex_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="archiveindex",
            name="end",
            field=models.DateTimeField(
                db_index=True,
                help_text="The point in time at which this archive stopped being valid.",
                null=True,
            ),
        ),
    ]
