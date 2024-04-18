from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from slm.api.edit import views as slm_views
from slm.map.api.edit.serializers import StationMapSerializer, StationSerializer


class StationListViewSet(slm_views.StationListViewSet):
    serializer_class = StationSerializer

    ordering_fields = (
        slm_views.StationListViewSet.ordering_fields
    )  # + ['latitude', 'longitude']

    def get_queryset(self):
        return super().get_queryset().with_location_fields("llh")


# todo we could use geodjango and gis drf extensions to do this automatically - but that produces a large dependency
#   overhead for a pretty basic task - revisit this if polygonal queries are deemed useful or other reasons to integrate
#   GIS features arise
class StationMapViewSet(StationListViewSet):
    """
    A view for returning a site list as a geojson set of point features. We
    inherit from our normal StationListViewSet so all filtering parameters are
    the same and we can pair requests to the map view with requests to the
    station list view.
    """

    serializer_class = StationMapSerializer
    pagination_class = None

    def list(self, request, **kwargs):
        return Response(
            {
                "type": "FeatureCollection",
                "features": self.get_serializer(
                    self.filter_queryset(self.get_queryset()), many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def get_queryset(self):
        return super().get_queryset().filter(Q(llh__isnull=False))
