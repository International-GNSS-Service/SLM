from enum import nonmember
from typing import Annotated

from django.utils.translation import gettext_lazy as _
from enum_properties import IntEnumProperties, Symmetric, symmetric


class MapBoxStyle(IntEnumProperties):
    """
    https://docs.mapbox.com/api/maps/styles/
    """

    name: Annotated[str, Symmetric()]
    label: Annotated[str, Symmetric(case_fold=True)]
    slug: Annotated[str, Symmetric(case_fold=True)]
    version: int

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    # name             value    label                slug           version
    STREETS           = 1, _("Streets"),           "streets",           12
    OUTDOORS          = 2, _("Outdoors"),          "outdoors",          12
    LIGHT             = 3, _("Light"),             "light",             11
    DARK              = 4, _("Dark"),              "dark",              11
    SATELLITE         = 5, _("Satellite"),         "satellite",          9
    SATELLITE_STREETS = 6, _("Satellite Streets"), "satellite-streets", 12
    NAVIGATION_DAY    = 7, _("Navigation Day"),    "navigation-day",     1
    NAVIGATION_NIGHT  = 8, _("Navigation Night"),  "navigation-night",   1
    # fmt: on

    @symmetric()
    @property
    def uri(self):
        return f"mapbox://styles/mapbox/{self.version_slug}"

    @property
    def version_slug(self):
        return f"{self.slug}-v{self.version}"

    def __str__(self):
        return self.uri


class MapBoxProjection(IntEnumProperties):
    """
    https://docs.mapbox.com/mapbox-gl-js/style-spec/projection/
    """

    name: Annotated[str, Symmetric()]
    label: Annotated[str, Symmetric()]
    slug: Annotated[str, Symmetric(case_fold=True)]

    do_not_call_in_templates = nonmember(True)

    # fmt: off
    # name                  value   label                        slug
    ALBERS                  = 0, _("Albers"),                  "albers"
    EQUAL_EARTH             = 1, _("Equal Earth"),             "equalEarth"
    EQUI_RECTANGULAR        = 2, _("Equi-Rectangular"),        "equirectangular"
    LAMBERT_CONFORMAL_CONIC = 3, _("Lambert Conformal Conic"), "lambertConformalConic"
    MERCATOR                = 4, _("Mercator"),                "mercator"
    NATURAL_EARTH           = 5, _("Natural Earth"),           "naturalEarth"
    WINKEL_TRIPEL           = 6, _("Winkel Tripel"),           "winkelTripel"
    GLOBE                   = 7, _("Globe"),                   "globe"
    # fmt: on

    def __str__(self):
        return self.slug
