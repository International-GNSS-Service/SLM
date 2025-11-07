"""
SLM URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/

Instead of having to define your own urls.py for a deployment of SLM we try to
do most of the work for you in this default file. If you develop an app and you
want it to be automatically included in your SLM urls you should add the flag
SLM_INCLUDE = True to your apps urls.py file. If you do so the urls in your
app will be included into your deployment at the / mount point. If you wish to
extend the APIs by providing your own endpoints you may do so by supplying an
APIS dictionary. For example the slm.map app extends the public API like so:

.. code-block: python

    from django.urls import path
    from slm.map.api.edit import views as edit_views
    from slm.map.api.public import views as public_views
    from slm.map.views import MapView

    SLM_INCLUDE = True

    APIS = {
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

"""

from importlib import import_module

from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from rest_framework.routers import DefaultRouter

APIS = {}


class ReregisterableRouter(DefaultRouter):
    def register(self, prefix, viewset, base_name=None):
        if base_name is None:
            base_name = self.get_default_base_name(viewset)
        idx = 0
        for api in self.registry:
            if prefix == api[0] and base_name == api[2]:
                self.registry[idx] = (prefix, viewset, base_name)
                idx += 1
                return
            idx += 1
        self.registry.append((prefix, viewset, base_name))


def bring_in_urls(urlpatterns):
    routers = {}

    for app in reversed(settings.INSTALLED_APPS):
        try:
            url_module_str = f"{app}.urls"
            url_module = import_module(url_module_str)
            slm_include = getattr(url_module, "SLM_INCLUDE", False)
            if not slm_include:
                continue
            api = getattr(url_module, "APIS", None)
            if api:
                for api, endpoints in api.items():
                    if api not in routers:
                        routers[api] = ReregisterableRouter()
                    router = routers[api]
                    for endpoint in endpoints:
                        router.register(
                            endpoint[0],
                            endpoint[1],
                            base_name=(
                                endpoint[0] if len(endpoint) < 3 else endpoint[2]
                            ),
                        )
            urlpatterns.insert(0, path("", include(url_module_str)))

        except ImportError:
            if app in {"slm", "slm.map", "slm.file_views", "network_map", "igs_ext"}:
                raise
            pass

    for api, router in routers.items():
        # todo how to nest under slm?
        pattern = path(
            f"api/{api}/", include((router.urls, "slm"), namespace=f"slm_{api}_api")
        )
        urlpatterns.append(pattern)
        APIS.setdefault(f"{api}_api", []).append(pattern)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("", include("slm.urls")),
    path("hijack/", include("hijack.urls")),
]

if getattr(settings, "SLM_DEBUG_TOOLBAR", False):
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))

# allows us to use static files like images
urlpatterns += staticfiles_urlpatterns()

bring_in_urls(urlpatterns)
