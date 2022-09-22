from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class MapBoxStyle(TextChoices):
    """
    https://docs.mapbox.com/api/maps/styles/
    """
    STREETS = 'streets', _('Streets')
    OUTDOORS = 'outdoors', _('Outdoors')
    LIGHT = 'light', _('Light')
    DARK = 'dark', _('Dark')
    SATELLITE = 'satellite', _('Satellite')
    SATELLITE_STREETS = 'satellite-streets', _('Satellite Streets')
    NAVIGATION_DAY = 'navigation-day', _('Navigation Day')
    NAVIGATION_NIGHT = 'navigation-night', _('Navigation Night')

    # this will have to be updated periodically to keep pace with mapbox style updates
    __versions__ = {
        STREETS[0]: 11,
        OUTDOORS[0]: 11,
        LIGHT[0]: 10,
        DARK[0]: 10,
        SATELLITE[0]: 9,
        SATELLITE_STREETS[0]: 11,
        NAVIGATION_DAY[0]: 1,
        NAVIGATION_NIGHT[0]: 1
    }

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str) and '-v' in value:
            return cls(value.split('-')[0])
        return super()._missing_(value)

    @property
    def version(self):
        return f'{self.value}-v{self.__versions__[self.value]}'

    @property
    def url(self):
        return f'mapbox://styles/mapbox/{self.version}'

    def __str__(self):
        return self.url


class MapBoxProjection(TextChoices):
    """
    https://docs.mapbox.com/mapbox-gl-js/style-spec/projection/
    """
    ALBERS = 'albers', _('Albers')
    EQUAL_EARTH = 'equalEarth', _('Equal Earth')
    EQUI_RECTANGULAR = 'equirectangular', _('Equi-Rectangular')
    LAMBERT_CONFORMAL_CONIC = 'lambertConformalConic', _('Lambert Conformal Conic')
    MERCATOR = 'mercator', _('Mercator')
    NATURAL_EARTH = 'naturalEarth', _('Natural Earth')
    WINKEL_TRIPEL = 'winkelTripel', _('Winkel Tripel')
    GLOBE = 'globe', _('Globe')

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str) and '-v' in value:
            return cls(value.split('-')[0])
        return super()._missing_(value)

    def __str__(self):
        return self.value
