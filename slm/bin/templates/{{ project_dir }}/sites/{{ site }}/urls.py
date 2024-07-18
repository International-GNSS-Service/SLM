from slm.settings.urls import urlpatterns
from django.urls import path, include

urlpatterns.extend([
    {% if not include_map %}#{% endif %}path('', include('slm.map.urls')),
    path('', include('{{ extension_app }}.urls')),
])
