# Generated by Django 4.1.7 on 2023-04-01 18:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "0001_alter_siteantenna_marker_enu_alter_sitelocation_llh_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dataavailability",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="data",
                to="slm.site",
            ),
        ),
    ]
