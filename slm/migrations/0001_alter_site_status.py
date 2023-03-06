# Generated by Django 4.1.4 on 2023-02-02 19:55

from django.db import migrations
import django_enum.fields


class Migration(migrations.Migration):

    dependencies = [
        ('slm', 'load_satellitesystems'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='status',
            field=django_enum.fields.EnumPositiveSmallIntegerField(blank=True, choices=[(1, 'Former'), (2, 'Proposed'), (3, 'Updated'), (4, 'Published'), (5, 'Empty'), (6, 'Suspended')], default=2, help_text='The current status of the site.'),
        ),
    ]