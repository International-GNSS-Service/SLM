"""
SLM URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

NOTES: 
This file handles mapping URLs to views.  Django makes it very easy
and straightforward.  Since SLM is the only app in this project,
the second statement in urlpatterns just directs us to the urls.py within
SLM.  Notice there are two urls.py files.  Adding "/admin" to local server
takes you to admin site which gives easy to use interface for admin controls. 

There are capabilities for URLs to take in parameters (i.e. station name, etc.).
This is not currently implemented, but it can be done easy.  See below:
https://docs.djangoproject.com/en/3.2/topics/http/urls/

To access admin site you will need an admin/superuser login.  See documentation
guide.
"""
from copy import deepcopy
from importlib import import_module

from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from slm.utils import SerializerRegistry

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
    import warnings

    routers = {}

    for app in reversed(settings.INSTALLED_APPS):
        if app.startswith('slm'):
            url_module = import_module(f'{app}.urls')
            if url_module:
                api = getattr(url_module, 'api', None)
                if api:
                    for api, config in api.items():
                        if api not in routers:
                            routers[api] = ReregisterableRouter()
                        router = routers[api]
                        if 'serializer_module' in config:
                            SerializerRegistry().add_modules(
                                api,
                                config['serializer_module'],
                                overwrite=True
                            )
                        else:
                            warnings.warn(
                                f'Expected `serializer_module` in '
                                f'{url_module.__name__}[api]'
                            )
                        if 'endpoints' in config:
                            for endpoint in config['endpoints']:
                                router.register(
                                    endpoint[0],
                                    endpoint[1],
                                    base_name=(
                                        endpoint[0] if len(endpoint) < 3
                                        else endpoint[2]
                                    )
                                )
                        else:
                            warnings.warn(
                                f'Expected `endpoints` in '
                                f'{url_module.__name__}[api]'
                            )

                if app != 'slm':
                    urlpatterns.append(
                        path('', include(f'{app}.urls', namespace=app))
                    )

                app_add_ons = getattr(url_module, 'add_ons', [])
                for add_on in app_add_ons:
                    urlpatterns.append(add_on)

    for api, router in routers.items():
        # todo how to nest under slm?
        pattern = path(
            f'api/{api}/',
            include((router.urls, 'slm'), namespace=f'slm_{api}_api')
        )
        urlpatterns.append(pattern)
        APIS.setdefault(f'{api}_api', []).append(pattern)


def api_patterns(api_namespace):
    return APIS.get(api_namespace, [])


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('slm.urls')),
]

if getattr(settings, 'DJANGO_DEBUG_TOOLBAR', False):
    urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))

# allows us to use static files like images
urlpatterns += staticfiles_urlpatterns()

bring_in_urls(urlpatterns)
