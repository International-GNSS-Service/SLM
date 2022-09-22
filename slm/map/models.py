from slm.models import SingletonModel
from slm.map.fields import (
    MapBoxStyleField,
    MapBoxProjectionField
)
from slm.map.defines import (
    MapBoxStyle,
    MapBoxProjection
)
from django.db import models
from django.utils.translation import gettext as _
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator
)


class MapSettings(SingletonModel):

    email = models.EmailField(
        null=True,
        blank=True,
        default=None,
        help_text=_('The mapbox account associated with the api key.')
    )

    api_key = models.CharField(
        default=None,
        null=True,
        blank=True,
        help_text=_('The API key for your mapbox account.'),
        max_length=255
    )

    map_style = MapBoxStyleField(
        null=False,
        blank=True,
        default=MapBoxStyle.LIGHT,
        help_text=_(
            _('The map tile styling to use.')
        )
    )

    map_projection = MapBoxProjectionField(
        null=False,
        blank=True,
        default=MapBoxProjection.GLOBE,
        help_text=_(
            _('The map projection to use.')
        )
    )

    zoom = models.FloatField(
        default=0.00001,
        null=False,
        blank=True,
        help_text=_('The default zoom level (0-22).'),
        validators=[MinValueValidator(0), MaxValueValidator(22)]
    )

    def __str__(self):
        return f'SLM Map Settings'

    class Meta:
        verbose_name = _('SLM Map Settings')
        verbose_name_plural = verbose_name
