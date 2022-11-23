from slm.models.system import (
    Agency,
    Alert,
    Network
)
from slm.models.user import (
    User,
    UserProfile
)
from slm.models.network import (
    NetworkInfo,
    Networksites,
    Networkscategory
)
from slm.models.data import DataAvailability
from slm.models.sitelog import (
    Site,
    SiteSection,
    SiteSubSection,
    SiteAntenna,
    SiteReceiver,
    SiteFrequencyStandard,
    SiteLocation,
    SiteLogStatus,
    SiteHumiditySensor,
    SiteForm,
    SiteIdentification,
    SiteCollocation,
    SiteMoreInformation,
    SitePressureSensor,
    SiteResponsibleAgency,
    SiteTemperatureSensor,
    SiteRadioInterferences,
    SiteSignalObstructions,
    SiteOperationalContact,
    SiteMultiPathSources,
    SiteOtherInstrumentation,
    SiteLocalEpisodicEffects,
    SiteWaterVaporRadiometer,
    SiteSurveyedLocalTies,
    LogEntry,
    AntennaType
)
from django.db import models
from django.core.cache import cache


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
