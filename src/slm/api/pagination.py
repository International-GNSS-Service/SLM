from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class BrowsablePagination(LimitOffsetPagination):
    default_limit = 100


class ClientPagination(LimitOffsetPagination):
    default_limit = 10


class DataTablesPagination(LimitOffsetPagination):
    default_limit = 20

    # datatables naming
    limit_query_param = "length"
    offset_query_param = "start"

    queryset = None
    draw = None

    def paginate_queryset(self, queryset, request, view=None):
        self.queryset = queryset
        self.draw = request.query_params.get("draw", None)
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        resp = {
            "data": data,
            "recordsTotal": self.queryset.model.objects.count(),
            "recordsFiltered": self.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
        }
        if self.draw is not None:
            resp["draw"] = self.draw
        return Response(resp)

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "recordsTotal": {
                    "type": "integer",
                    "example": 123,
                },
                "recordsFiltered": {"type": "integer", "example": 123},
                "draw": {"type": "integer", "nullable": True, "example": 1},
                "data": schema,
            },
        }

    def get_results(self, data):
        return data["data"]
