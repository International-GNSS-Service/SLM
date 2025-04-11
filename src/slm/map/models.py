from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext as _
from django_enum import EnumField

from slm.map.defines import MapBoxProjection, MapBoxStyle
from slm.singleton import SingletonModel


class MapSettings(SingletonModel):
    email = models.EmailField(
        null=True,
        blank=True,
        default=None,
        help_text=_("The mapbox account associated with the api key."),
    )

    api_key = models.CharField(
        default=None,
        null=True,
        blank=True,
        help_text=_("The API key for your mapbox account."),
        max_length=255,
    )

    map_style = EnumField(
        MapBoxStyle,
        null=False,
        blank=False,
        default=MapBoxStyle.LIGHT,
        help_text=_(_("The map tile styling to use on the interactive map page.")),
    )

    map_projection = EnumField(
        MapBoxProjection,
        null=False,
        blank=False,
        default=MapBoxProjection.GLOBE,
        help_text=_(_("The map projection to use on the interactive map page.")),
    )

    zoom = models.FloatField(
        default=2,
        null=False,
        blank=True,
        help_text=_("The default zoom level (0-22)."),
        validators=[MinValueValidator(0), MaxValueValidator(22)],
    )

    static_map_style = EnumField(
        MapBoxStyle,
        null=False,
        blank=False,
        default=MapBoxStyle.LIGHT,
        help_text=_(_("The map tile styling to use for static map images.")),
    )

    def __str__(self):
        return "SLM Map Settings"

    class Meta:
        verbose_name = _("SLM Map Settings")
        verbose_name_plural = verbose_name
