# Generated by Django 4.1.7 on 2023-03-31 18:31

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "load_satellitesystems"),
    ]

    operations = [
        migrations.AlterField(
            model_name="siteantenna",
            name="marker_enu",
            field=django.contrib.gis.db.models.fields.PointField(
                dim=3,
                help_text="East-North-Up eccentricity is the offset between the ARP and marker described in section 1 measured to an accuracy of 1mm. Format: (F8.4) Value 0 is OK",
                srid=0,
                verbose_name="Marker->ARP ENU Ecc (m)",
            ),
        ),
        migrations.AlterField(
            model_name="sitelocation",
            name="llh",
            field=django.contrib.gis.db.models.fields.PointField(
                db_index=True,
                dim=3,
                help_text="Enter the ITRF latitude and longitude in decimal degrees and elevation in meters to one meter precision. Note, legacy site log format is (+/-DDMMSS.SS) and elevation may be given to more decimal places than F7.1. F7.1 is the minimum for the SINEX format.",
                null=True,
                srid=4979,
                verbose_name="Position (Lat, Lon, Elev (m))",
            ),
        ),
        migrations.AlterField(
            model_name="sitelocation",
            name="xyz",
            field=django.contrib.gis.db.models.fields.PointField(
                db_index=True,
                dim=3,
                help_text="Enter the ITRF position to a one meter precision. Format (m)",
                null=True,
                srid=7789,
                verbose_name="Position (X, Y, Z) (m)",
            ),
        ),
    ]
