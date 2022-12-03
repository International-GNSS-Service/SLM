from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from slm.models.system import (
    Agency,
    Alert,
    Network,
    ReviewRequest,
    SatelliteSystem,
    Antenna,
    Receiver,
    Radome,
    Manufacturer,
    SiteFileUpload,
    RenderedSiteLog,
    LogEntry
)
from slm.models.user import (
    User,
    UserProfile
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
    SiteSurveyedLocalTies
)
from django.db import models
from django.core.cache import cache

_site_record = None


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


def get_record_model():
    global _site_record
    if _site_record is not None:
        return _site_record

    from django.apps import apps
    slm_site_record = getattr(
        settings,
        'SLM_SITE_RECORD',
        'slm.DefaultSiteRecord'
    )
    try:
        app_label, model_class = slm_site_record.split('.')
        _site_record = apps.get_app_config(
            app_label
        ).get(model_class.lower(), None)
        if not _site_record:
            raise ImproperlyConfigured(
                f'SLM_SITE_RECORD "{slm_site_record}" is not a registered '
                f'model'
            )
        return _site_record
    except ValueError as ve:
        raise ImproperlyConfigured(
            f'SLM_SITE_RECORD value {slm_site_record} is invalid, must be '
            f'"app_label.ModelClass"'
        ) from ve

