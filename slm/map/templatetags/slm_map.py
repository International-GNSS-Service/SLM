from django import template

from slm.map.models import MapSettings

register = template.Library()


@register.filter(name="map_position_img")
def map_position_img(lat_lng):
    if lat_lng:
        settings = MapSettings.load()
        return (
            f"https://api.mapbox.com/styles/v1/mapbox/"
            f"{settings.static_map_style.version_slug}/static/"
            f"pin-s+000({lat_lng[1]},{lat_lng[0]})/0,0,0,0,0/"
            f"540x540@2x?access_token={settings.api_key}"
        )
    return ""
