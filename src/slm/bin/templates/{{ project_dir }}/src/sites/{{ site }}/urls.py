"""
You can make direct modifications to the URLs built by the slm here if needed.

Your extension app will already be included at the root path because it sets:

    SLM_INCLUDE = True.
"""

from slm.settings.urls import urlpatterns
from django.urls import path, include


urlpatterns.extend([
    # add other app URLs here
])
