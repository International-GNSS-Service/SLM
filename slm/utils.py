import importlib
import inspect
import sys
from logging import Filter
from pprint import pformat
from rest_framework.serializers import Serializer
from django.conf import settings
from lxml.etree import Resolver


PROTOCOL = getattr(settings, 'SLM_HTTP_PROTOCOL', None)


def set_protocol(request):
    global PROTOCOL
    if not PROTOCOL:
        PROTOCOL = 'https' if request.is_secure() else 'http'


def get_protocol():
    global PROTOCOL
    if PROTOCOL is not None:
        return PROTOCOL
    return (
        'https'
        if getattr(settings, 'SECURE_SSL_REDIRECT', False) else
        'http'
    )


def build_absolute_url(path, request=None):
    if request:
        return request.build_absolute_uri(path)
    return f'{get_url()}/{path.lstrip("/")}'


def get_url():
    from django.contrib.sites.models import Site
    return f'{get_protocol()}://{Site.objects.get_current().domain}'


def from_email():
    from django.contrib.sites.models import Site
    return getattr(
        settings,
        'DEFAULT_FROM_EMAIL',
        f'noreply@{Site.objects.get_current().domain}'
    )


class SquelchStackTraces(Filter):

    def filter(self, record):
        record.exc_info = None
        return super().filter(record)


def to_bool(bool_str):
    if bool_str is None:
        return None
    if isinstance(bool_str, str):
        return not bool_str.lower() in ['0', 'no', 'false']
    return bool(bool_str)


def to_snake_case(string):
    snake = string
    if string:
        snake = string[0].lower()
        new = False
        for char in string[1:]:
            if char == ' ':
                new = True
            elif char.isupper() or new:
                snake += f'_{char.lower()}'
                new = False
            elif char.isalnum():
                snake += char
    return snake


def date_to_str(date_obj):
    if date_obj:
        return f'{date_obj.year}-{date_obj.month:02}-{date_obj.day:02}'
    return ''


class _Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        '''
        elif len(args) > 0:
            config = { }
            for idx, arg in enumerate(args):
                config[idx] = arg
            raise ValueError( self.__class__.__name__ + ' can only be initialized with a configuration once!', config )
        '''

        return cls._instances[cls]

    @classmethod
    def is_instantiated(cls, typ):
        return typ in cls._instances

    @classmethod
    def destroy(cls, typ):
        if typ in cls._instances:
            del cls._instances[typ]


class Singleton(_Singleton('SingletonMeta', (object,), {})):
    pass


class SerializerRegistry(Singleton):
    """
    This class provides a way to register and fetch serialization routines
    for specific model types. For example if for some reason you wanted to
    serialize all the Sites through the client api you could do:

        ..code-block::

            from core.models import Box
            from rest_framework.renderers import JSONRenderer

            JSONRenderer().render(
                SerializerRegistry().get_serializer('edit', type(Site))(
                    Site.objects.all(), many=True
                ),
                accepted_media_type='Accept: application/json; indent=4'
            ).decode('utf-8')
    """
    serializer_map = {}
    proxy_map = {}

    def initialized(self):
        return len(self.serializer_map) > 0

    def add_named_serializer(self, api, name, serializer_cls):
        self.serializer_map[api][name] = serializer_cls

    def add_modules(self, api, modules, overwrite=False):
        if isinstance(modules, str):
            modules = [modules]
        if api not in self.serializer_map:
            self.serializer_map[api] = {}
        for module in modules:
            importlib.import_module(module)
            for name, obj in inspect.getmembers(sys.modules[module]):
                if inspect.isclass(obj) and Serializer in obj.__mro__ and hasattr(obj, 'Meta'):
                    if not getattr(obj.Meta, 'abstract', None) and not getattr(obj.Meta, 'exclude_from_registry', None):
                        registry_name = getattr(obj.Meta, 'registry_name', None)
                        if registry_name:
                            if overwrite or registry_name not in self.serializer_map[api]:
                                self.serializer_map[api][registry_name] = obj
                        elif overwrite or obj.Meta.model not in self.serializer_map[api]:
                            self.serializer_map[api][obj.Meta.model] = obj

    def add_proxy_model(self, api, proxy, model, overwrite=False):
        api = self.proxy_map.setdefault(api, {})
        if not overwrite and proxy in api:
            return
        api[proxy] = model

    def get_serializer(self, api, typ_or_name):
        if not isinstance(typ_or_name, str) and not isinstance(typ_or_name, type):
            typ_or_name = type(typ_or_name)
        if api not in self.serializer_map:
            return None
        if typ_or_name not in self.serializer_map[api]:
            if typ_or_name in self.proxy_map.get(api, {}):
                return self.get_serializer(api, self.proxy_map[api][typ_or_name])
            return None
        return self.serializer_map[api][typ_or_name]

    def get_proxies(self, api, model):
        if api not in self.proxy_map:
            return None
        proxies = []
        for proxy, proxied in self.proxy_map[api].items():
            if model is proxied:
                proxies.append(proxy)
        if len(proxies) > 0:
            return proxies
        return None

    def __str__(self):
        return pformat(self.serializer_map)
