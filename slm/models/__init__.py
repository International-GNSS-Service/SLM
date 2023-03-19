from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from slm.models.data import DataAvailability
from slm.models.index import ArchivedSiteLog, ArchiveIndex
from slm.models.sitelog import (
    Site,
    SiteAntenna,
    SiteCollocation,
    SiteForm,
    SiteFrequencyStandard,
    SiteHumiditySensor,
    SiteIdentification,
    SiteLocalEpisodicEffects,
    SiteLocation,
    SiteMoreInformation,
    SiteMultiPathSources,
    SiteOperationalContact,
    SiteOtherInstrumentation,
    SitePressureSensor,
    SiteRadioInterferences,
    SiteReceiver,
    SiteResponsibleAgency,
    SiteSection,
    SiteSignalObstructions,
    SiteSubSection,
    SiteSurveyedLocalTies,
    SiteTemperatureSensor,
    SiteWaterVaporRadiometer,
)
from slm.models.equipment import (
    Equipment,
    Antenna,
    Manufacturer,
    Receiver,
    Radome,
    SatelliteSystem,
    AntCal
)
from slm.models.system import (
    Agency,
    LogEntry,
    Network,
    SiteFile,
    SiteFileUpload,
    TideGauge,
    SiteTideGauge
)
from slm.models.alerts import (
    Alert,
    UserAlert,
    SiteAlert,
    AgencyAlert,
    GeodesyMLInvalid,
    ReviewRequested,
    UpdatesRejected,
    ImportAlert
)
from slm.models.user import User, UserProfile

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

from slm.models.help import Help
from slm.models.about import About
