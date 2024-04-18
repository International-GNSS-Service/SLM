from rest_framework import pagination
from rest_framework.response import Response

from slm.api.public import views as slm_views
from slm.map.api.public.serializers import StationListSerializer, StationMapSerializer
from slm.models import Site


class StationListViewSet(slm_views.StationListViewSet):
    serializer_class = StationListSerializer

    # could add fields here to extend ordering options
    ordering_fields = slm_views.StationListViewSet.ordering_fields

    def get_queryset(self):
        # could add additional filter parameters or annotations here to extend the api
        return super().get_queryset()


class FeatureCollectionPagination(pagination.BasePagination):
    """
    We implement geojson wrapper as a special type of pagination even though
    no paging is done. This method fits neatly into how the base classes
    generate and process response objects. Doing this directly in list()
    on the view breaks filter form rendering in the browsable renderers.
    """

    def paginate_queryset(self, queryset, request, view=None):
        return queryset

    def to_html(self):
        return None

    def get_results(self, data):
        return data["features"]

    def get_paginated_response(self, data):
        return Response({"type": "FeatureCollection", "features": data})

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "example": "FeatureCollection",
                },
                "features": schema,
            },
        }


class StationMapViewSet(StationListViewSet):
    """
    A view for returning a site list as a geojson set of point features.
    """

    serializer_class = StationMapSerializer
    pagination_class = FeatureCollectionPagination

    def get_queryset(self):
        return (
            Site.objects.with_location_fields("llh").public().availability().distinct()
        )
