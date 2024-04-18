# Generated by Django 3.2.16 on 2022-12-08 09:41

import django.core.validators
import django_enum.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MapSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        default=None,
                        help_text="The mapbox account associated with the api key.",
                        max_length=254,
                        null=True,
                    ),
                ),
                (
                    "api_key",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="The API key for your mapbox account.",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "map_style",
                    django_enum.fields.EnumPositiveSmallIntegerField(
                        choices=[
                            (1, "Streets"),
                            (2, "Outdoors"),
                            (3, "Light"),
                            (4, "Dark"),
                            (5, "Satellite"),
                            (6, "Satellite Streets"),
                            (7, "Navigation Day"),
                            (8, "Navigation Night"),
                        ],
                        default=3,
                        help_text="The map tile styling to use on the interactive map page.",
                    ),
                ),
                (
                    "map_projection",
                    django_enum.fields.EnumPositiveSmallIntegerField(
                        choices=[
                            (0, "Albers"),
                            (1, "Equal Earth"),
                            (2, "Equi-Rectangular"),
                            (3, "Lambert Conformal Conic"),
                            (4, "Mercator"),
                            (5, "Natural Earth"),
                            (6, "Winkel Tripel"),
                            (7, "Globe"),
                        ],
                        default=7,
                        help_text="The map projection to use on the interactive map page.",
                    ),
                ),
                (
                    "zoom",
                    models.FloatField(
                        blank=True,
                        default=2,
                        help_text="The default zoom level (0-22).",
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(22),
                        ],
                    ),
                ),
                (
                    "static_map_style",
                    django_enum.fields.EnumPositiveSmallIntegerField(
                        choices=[
                            (1, "Streets"),
                            (2, "Outdoors"),
                            (3, "Light"),
                            (4, "Dark"),
                            (5, "Satellite"),
                            (6, "Satellite Streets"),
                            (7, "Navigation Day"),
                            (8, "Navigation Night"),
                        ],
                        default=3,
                        help_text="The map tile styling to use for static map images.",
                    ),
                ),
            ],
            options={
                "verbose_name": "SLM Map Settings",
                "verbose_name_plural": "SLM Map Settings",
            },
        ),
    ]
