from slm.defines import SiteLogStatus
from slm.map.models import MapSettings
from slm.models import Agency, Network, Site, SiteLocation
from slm.views import SLMView


class MapView(SLMView):
    template_name = "slm/map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agency = kwargs.get("agency", None)
        if agency:
            agency = Agency.objects.get(name=agency)

        network = kwargs.get("network", None)
        if network:
            network = Network.objects.get(name=network)

        map_settings = MapSettings.load()
        context.update(
            {
                "api_key": map_settings.api_key,
                "map_style": str(map_settings.map_style),
                "projection": str(map_settings.map_projection),
                "zoom": map_settings.zoom,
                "agency": agency,
                "network": network,
                "Site": Site,
                "SiteLocation": SiteLocation,
                "SiteLogStatus": SiteLogStatus,
                "agencies": Agency.objects.membership(user=self.request.user),
                "networks": Network.objects.all(),
            }
        )
        return context
