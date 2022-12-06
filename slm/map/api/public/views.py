from slm.api.public import views as slm_views
from django.db.models import (
    Subquery,
    OuterRef,
    Q
)
from slm.models import SiteLocation
from slm.map.api.public.serializers import (
    StationListSerializer,
    StationMapSerializer
)
from rest_framework.response import Response
from rest_framework import status


class StationListViewSet(slm_views.StationListViewSet):

    serializer_class = StationListSerializer

    # could add fields here to extend ordering options
    ordering_fields = slm_views.StationListViewSet.ordering_fields

    def get_queryset(self):
        # could add additional filter parameters or annotations here to extend the api
        return super().get_queryset()


# todo we could use geodjango and gis drf extensions to do this automatically - but that produces a large dependency
#   overhead for a pretty basic task - revisit this if polygonal queries are deemed useful or other reasons to integrate
#   GIS features arise
class StationMapViewSet(StationListViewSet):
    """
    A view for returning a site list as a geojson set of point features.
    """

    serializer_class = StationMapSerializer
    pagination_class = None

    def list(self, request, **kwargs):
        return Response({
            'type': 'FeatureCollection',
            'features':  self.get_serializer(
                self.filter_queryset(self.get_queryset()), many=True
            ).data
        }, status=status.HTTP_200_OK)

    def get_queryset(self):
        return super().get_queryset().filter(
            Q(latitude__isnull=False) & Q(longitude__isnull=False)
        )
