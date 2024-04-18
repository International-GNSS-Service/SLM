from django.core.cache import cache
from django.db import models


class _Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]

    @classmethod
    def is_instantiated(cls, typ):
        return typ in cls._instances

    @classmethod
    def destroy(cls, typ):
        if typ in cls._instances:
            del cls._instances[typ]


class Singleton(_Singleton("SingletonMeta", (object,), {})):
    pass


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        pass

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)
        self.set_cache()

    @classmethod
    def load(cls):
        if cache.get(cls.__name__) is None:
            obj, created = cls.objects.get_or_create(pk=1)
            if not created:
                obj.set_cache()
        return cache.get(cls.__name__)

    def set_cache(self):
        cache.set(self.__class__.__name__, self)
