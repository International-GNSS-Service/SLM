# Generated by Django 3.2.15 on 2022-09-23 20:02

import django.core.validators
from django.db import migrations, models
import django_enum.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MapSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(blank=True, default=None, help_text='The mapbox account associated with the api key.', max_length=254, null=True)),
                ('api_key', models.CharField(blank=True, default=None, help_text='The API key for your mapbox account.', max_length=255, null=True)),
                ('map_style', django_enum.fields.EnumCharField(blank=True, choices=[('streets', 'Streets'), ('outdoors', 'Outdoors'), ('light', 'Light'), ('dark', 'Dark'), ('satellite', 'Satellite'), ('satellite-streets', 'Satellite Streets'), ('navigation-day', 'Navigation Day'), ('navigation-night', 'Navigation Night')], default='light', help_text='The map tile styling to use.', max_length=17)),
                ('map_projection', django_enum.fields.EnumCharField(blank=True, choices=[('albers', 'Albers'), ('equalEarth', 'Equal Earth'), ('equirectangular', 'Equi-Rectangular'), ('lambertConformalConic', 'Lambert Conformal Conic'), ('mercator', 'Mercator'), ('naturalEarth', 'Natural Earth'), ('winkelTripel', 'Winkel Tripel'), ('globe', 'Globe')], default='globe', help_text='The map projection to use.', max_length=21)),
                ('zoom', models.FloatField(blank=True, default=1e-05, help_text='The default zoom level (0-22).', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(22)])),
            ],
            options={
                'verbose_name': 'SLM Map Settings',
                'verbose_name_plural': 'SLM Map Settings',
            },
        ),
    ]