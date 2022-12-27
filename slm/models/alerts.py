from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _
from django.conf import settings
from slm.defines import (
    AlertLevel,
    GeodesyMLVersion,
    SLMFileType,
    SiteLogFormat
)
from slm import signals as slm_signals
from slm.models.system import SiteFile
from polymorphic.models import PolymorphicModel
from polymorphic.managers import PolymorphicManager, PolymorphicQuerySet
from django.utils.timezone import now
from django_enum import EnumField
from slm.parsing.xsd import SiteLogParser
from django.core.files.base import ContentFile
from django.template.loader import get_template
from django.contrib.sites.models import Site as DjangoSite
from django.core.mail import send_mail
from django.core.exceptions import ImproperlyConfigured
from logging import getLogger
from smtplib import SMTPException
import os


class AlertManager(PolymorphicManager):

    ALERT_MODELS = {}

    # automated alerts should set this set to this list of signals
    # that may trigger the alert
    SUPPORTED_SIGNALS = set()

    @classmethod
    def _init_alert_models_(cls):
        """
        We lazily init these maps so we only have to do this work once and
        our polymorphic queries can pick out the correct related alerts.
        :return:
        """
        if cls.ALERT_MODELS:
            return
        from django.apps import apps
        from django.core.exceptions import FieldDoesNotExist
        from slm.models import Site, Agency
        from django.contrib.auth import get_user_model
        cls.ALERT_MODELS = {
            'untargeted': set(),
            'site': set(),
            'agency': set(),
            'user': set()
        }
        relations = [
            {'model': Site, 'field': 'site'},
            {'model': Agency, 'field': 'agency'},
            {'model': get_user_model(), 'field': 'user'},
        ]
        for app in apps.get_app_configs():
            for model in app.get_models():
                if issubclass(model, Alert):
                    found_relation = False
                    for relation in relations:
                        try:
                            if issubclass(
                                model._meta.get_field(
                                    relation['field']
                                ).related_model,
                                relation['model']
                            ):
                                found_relation = True
                                cls.ALERT_MODELS[relation['field']].add(model)
                        except FieldDoesNotExist:
                            continue
                    if not found_relation:
                        cls.ALERT_MODELS['untargeted'].add(model)

    @classmethod
    def site_alerts(cls):
        cls._init_alert_models_()
        return cls.ALERT_MODELS['site']

    @classmethod
    def agency_alerts(cls):
        cls._init_alert_models_()
        return cls.ALERT_MODELS['agency']

    @classmethod
    def user_alerts(cls):
        cls._init_alert_models_()
        return cls.ALERT_MODELS['user']

    @classmethod
    def untargeted_alerts(cls):
        cls._init_alert_models_()
        return cls.ALERT_MODELS['untargeted']

    def from_signal(self, **kwargs):
        raise NotImplementedError(
            f'{self.__class__} must implement from_signal() to trigger alerts '
            f'from a signal.'
        )

    def classes(self):
        from django.apps import apps
        classes = set()
        for app_config in apps.get_app_configs():
            for mdl in app_config.get_models():
                if isinstance(mdl, self.model):
                    classes.add(mdl)
        return classes


class AlertQuerySet(PolymorphicQuerySet):

    def delete_expired(self):
        self.filter(expires__lte=now()).delete()

    def for_site(self, site):
        if not site:
            return self.none()
        return self.filter(self.site_q(site))

    def for_sites(self, sites):
        if not sites:
            return self.none()
        return self.filter(self.sites_q(sites))

    def for_agencies(self, agencies):
        if not agencies:
            return self.none()
        return self.filter(self.agencies_q(agencies))

    def for_user(self, user):
        if user.is_authenticated:
            return self.filter(self.user_q(user))
        return self.none()

    @classmethod
    def user_q(cls, user):
        qry = Q()
        for alert_class in AlertManager.user_alerts():
            qry |= Q(**{f'{alert_class._meta.model_name}__user': user})
        return qry

    @classmethod
    def sites_q(cls, sites):
        qry = Q()
        for alert_class in AlertManager.site_alerts():
            qry |= Q(**{f'{alert_class._meta.model_name}__site__in': sites})
        return qry

    @classmethod
    def site_q(cls, sites):
        qry = Q()
        for alert_class in AlertManager.site_alerts():
            qry |= Q(**{f'{alert_class._meta.model_name}__site': sites})
        return qry

    @classmethod
    def agencies_q(cls, agencies):
        qry = Q()
        for alert_class in AlertManager.agency_alerts():
            qry |= Q(**{
                f'{alert_class._meta.model_name}__agency__in': agencies
            })
        return qry

    @classmethod
    def untargeted_q(cls):
        qry = Q()
        for alert_class in AlertManager.agency_alerts():
            qry |= Q(instance_of=alert_class)
        return qry

    def visible_to(self, user):
        from slm.models import Site
        if user.is_authenticated:
            if user.is_superuser:
                return self.all()
            else:
                return self.filter(
                    self.untargeted_q() |
                    self.user_q(user) |
                    self.sites_q(Site.objects.editable_by(user)) |
                    self.agencies_q(user.agencies.all())
                )
        return self.none()

    def send_email(self):
        for alert in self:
            alert.send_email()


class Alert(PolymorphicModel):

    # automated alert types are only issued by the system
    automated = False

    template_txt = 'slm/emails/alert_issued.txt'
    template_html = 'slm/emails/alert_issued.html'

    logger = getLogger()

    @property
    def context(self):
        return {
            'alert': self
        }

    @property
    def target(self):
        return None

    @property
    def users(self):
        """
        Return a queryset that contains all targeted users and any relevant
        moderators that may be interested in the alert.

        :return: User QuerySet
        """
        from django.contrib.auth import get_user_model
        if self.__class__ in self.objects.ALERT_MODELS.get('untargeted', {}):
            return get_user_model().objects.all()
        if self.__class__ in self.objects.ALERT_MODELS.get('agency', {}):
            return get_user_model().objects.filter(
                Q(agencies__in=[self.agency]) |
                Q(is_superuser=True)
            )
        if self.__class__ in self.objects.ALERT_MODELS.get('site', {}):
            return get_user_model().objects.filter(
                Q(pk__in=self.site.editors()) |
                Q(pk__in=self.site.moderators())
            )
        if self.__class__ in self.objects.ALERT_MODELS.get('user', {}):
            return get_user_model().objects.filter(
                Q(pk=self.user.pk) |
                Q(is_superuser=True)
            )
        raise RuntimeError(
            f'Unable to determine targeted users for alert: {self}'
        )

    issuer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True
    )

    header = models.CharField(
        max_length=50,
        null=False,
        default='',
        help_text=_('A short description of the alert.')
    )
    detail = models.TextField(
        blank=True,
        null=False,
        default='',
        help_text=_('Longer description containing details of the alert.')
    )

    level = EnumField(AlertLevel, null=False, blank=False, db_index=True)

    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text=_('The time the alert was created.'),
        db_index=True
    )

    sticky = models.BooleanField(
        default=False,
        blank=True,
        help_text=_(
            'Do not allow target users to clear this alert, only admins may '
            'clear.'
        )
    )

    expires = models.DateTimeField(
        null=True,
        default=None,
        blank=True,
        help_text=_('Automatically remove this alert after this time.'),
        db_index=True
    )

    send_email = models.BooleanField(
        default=False,
        null=False,
        blank=False,
        help_text=_(
            'If true, an email will be sent for this alert to every targeted '
            'user.'
        )
    )

    objects = AlertManager.from_queryset(AlertQuerySet)()

    def send_emails(self):
        """
        Send an email to all targeted recipients about this alert.

        :return: True if the email was sent successfully - false otherwise
        """
        text = get_template(self.template_txt)
        html = get_template(self.template_html)
        html_ok = not (self.users.emails_ok(html=False).count())

        try:
            send_mail(
                subject=f'[{DjangoSite.objects.get_current().name}] {self}',
                from_email=getattr(
                    settings,
                    'DEFAULT_FROM_EMAIL',
                    f'noreply@{DjangoSite.objects.first().domain}'
                ),
                message=text.render(self.context),
                recipient_list=(user.email for user in self.users.emails_ok()),
                fail_silently=False,
                html_message=html.render(self.context) if html_ok else None
            )
        except SMTPException as smtp_exc:
            self.logger.exception(smtp_exc)
            return False

    def __str__(self):
        return self.header

    class Meta:
        ordering = ('-timestamp',)
        verbose_name_plural = 'Alerts'


class SiteAlert(Alert):

    site = models.ForeignKey(
        'slm.Site',
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_(
            'Only users with access to this site will see this alert.'
        ),
        related_name='alerts'
    )

    @property
    def target(self):
        return self.site

    def __str__(self):
        if self.site:
            return f'{self.site.name}: {super().__str__()}'
        return super().__str__()

    class Meta:
        verbose_name_plural = 'Site Alerts'


class UserAlert(Alert):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_('Only this user will see this alert.'),
        related_name='alerts'
    )

    @property
    def target(self):
        return self.user

    class Meta:
        verbose_name_plural = 'User Alerts'


class AgencyAlert(Alert):

    agency = models.ForeignKey(
        'slm.Agency',
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_('Only members of this agency will see this alert.'),
        related_name='alerts'
    )

    @property
    def target(self):
        return self.agency

    class Meta:
        verbose_name_plural = 'Agency Alerts'


class AutomatedAlertMixin:

    automated = True

    def save(self, *args, **kwargs):
        for key, val in getattr(
            settings, 'SLM_AUTOMATED_ALERTS', {}
        ).get('slm.GeodesyMLInvalid', {}).items():
            if key in {'signals'}:
                continue
            setattr(self, key, val)
        super().save(*args, **kwargs)


class GeodesyMLInvalidManager(AlertManager):

    SUPPORTED_SIGNALS = {
        slm_signals.site_published,
        slm_signals.site_status_changed,
        slm_signals.section_added,
        slm_signals.section_edited,
        slm_signals.section_deleted,
        slm_signals.site_file_published,
        slm_signals.site_file_unpublished
    }

    def from_signal(self, signal, site=None, **kwargs):
        """
        Check if an alert should be issued when the given signal is dispatched
        and issue the alert if necessary.

        :param signal:
        :param site:
        :param kwargs:
        :return: The alert that was issued if
        """
        if signal not in self.SUPPORTED_SIGNALS:
            raise ImproperlyConfigured(
                f'GeodesyMLInvalid alerts must be triggered by a supported '
                f'signal: {self.SUPPORTED_SIGNALS}'
            )
        site.refresh_from_db()
        return self.check_site(site=site)

    def check_site(self, site, published=None):
        """
        Check if this alert should be issued for the given site. If an alert
        should be issued and a current one exists for this site, the current
        one will be deleted before the new alert is issued.

        :param site: The Site object to check.
        :param published: If True, check the published version of this site's
            log - otherwise check the HEAD version, which may contain updates
        :return: The alert object if one was issued, None otherwise
        """
        from slm.api.serializers import SiteLogSerializer
        if hasattr(site, 'schema_alert') and site.schema_alert:
            if os.path.exists(site.schema_alert.file.path):
                os.remove(site.schema_alert.file.path)
            site.schema_alert.delete()

        geo_version = GeodesyMLVersion.latest()
        serializer = SiteLogSerializer(instance=site, published=published)
        xml_str = serializer.format(
            SiteLogFormat.GEODESY_ML,
            version=geo_version
        )
        parser = SiteLogParser(xml_str.decode())
        if parser.errors:
            return self.model.objects.create(
                published=serializer.is_published,
                site=site,
                schema=geo_version,
                findings={
                    lineno: (err.level, err.message)
                    for lineno, err in parser.errors.items()
                },
                file=ContentFile(
                    xml_str,
                    name=site.get_filename(log_format=SiteLogFormat.GEODESY_ML)
                )
            )
        return None


class GeodesyMLInvalidQuerySet(AlertQuerySet):

    def check_all(self, published=None):
        """
        Check if an alert should be issued for all sites in this QuerySet.

        :param published: If True, check the published version of this site's
            log - otherwise check the HEAD version, which may contain updates
        :return: The number of alerts issued.
        """
        alerts = 0
        for site in self:
            if GeodesyMLInvalidManager.objects.check_site(
                site, published=published
            ):
                alerts += 1
        return alerts


class GeodesyMLInvalid(AutomatedAlertMixin, SiteFile, Alert):

    SUB_DIRECTORY = 'alerts'

    @property
    def context(self):
        return {
            **super().context,
            'findings': self.findings,
            'site': self.site,
            'file': self
        }

    @property
    def target(self):
        return self.site

    timestamp = Alert.timestamp

    site = models.OneToOneField(
        'slm.Site',
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_(
            'This site this alert applies to.'
        ),
        related_name='schema_alert'
    )

    findings = models.JSONField()

    schema = EnumField(
        GeodesyMLVersion,
        null=False,
        default=GeodesyMLVersion.latest(),
        help_text=_('The schema version that failed validation.')
    )

    published = models.BooleanField(
        null=False,
        help_text=_(
            'True if this alert was issued from the published version of the '
            'site log.'
        )
    )

    objects = GeodesyMLInvalidManager.from_queryset(GeodesyMLInvalidQuerySet)()

    def save(self, *args, **kwargs):
        self.mimetype = SiteLogFormat.GEODESY_ML.mimetype
        self.file_type = SLMFileType.SITE_LOG
        self.log_format = SiteLogFormat.GEODESY_ML
        self.header = _('GeodesyML is Invalid.')
        self.detail = _(
            'The data for this site does not validate against GeodesyML '
            'schema version: '
        ) + str(self.schema)
        self.sticky = False
        self.expires = None
        self.send_email = False
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('site',)
