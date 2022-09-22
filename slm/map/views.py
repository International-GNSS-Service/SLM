from django.views.generic import TemplateView
from slm.map.models import MapSettings
from slm.models import (
    Site,
    SiteLocation,
    Agency
)
from slm.defines import SiteLogStatus
from slm.views import SLMView


class MapView(SLMView):
    template_name = 'slm/map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agency = kwargs.get('agency', None)
        if agency:
            agency = Agency.objects.get(name=agency)

        map_settings = MapSettings.load()
        context.update({
            'api_key': map_settings.api_key,
            'map_style': str(map_settings.map_style),
            'projection': str(map_settings.map_projection),
            'zoom': map_settings.zoom,
            'agency': agency,
            'Site': Site,
            'SiteLocation': SiteLocation,
            'SiteLogStatus': SiteLogStatus,
            'agencies': Agency.objects.accessible_by(user=self.request.user)
        })
        return context
