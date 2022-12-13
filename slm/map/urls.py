from django.urls import path
from slm.map.api.edit import views as edit_views
from slm.map.api.public import views as public_views
from slm.map.views import MapView

api = {
    'edit': {
        'serializer_module': 'slm.map.api.edit.serializers',
        'endpoints': [
            ('stations', edit_views.StationListViewSet),
            ('map', edit_views.StationMapViewSet),
        ]
    },
    'public': {
        'serializer_module': 'slm.map.api.public.serializers',
        'endpoints': [
            ('stations', public_views.StationListViewSet),
            ('map', public_views.StationMapViewSet),
        ]
    }
}

app_name = 'slm_map'

urlpatterns = [
    path('map/', MapView.as_view(), name='map'),
    path('map/<str:agency>', MapView.as_view(), name='map'),
]
