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
from slm.utils import from_email
from polymorphic.models import PolymorphicModel
from polymorphic.managers import PolymorphicManager, PolymorphicQuerySet
from django.utils.timezone import now
from django_enum import EnumField
from slm.parsing.xsd import SiteLogParser
from django.core.files.base import ContentFile
from django.template.loader import get_template
from django.contrib.sites.models import Site as DjangoSite
from django.core.exceptions import ImproperlyConfigured
from logging import getLogger
from smtplib import SMTPException
from django.core.mail import EmailMultiAlternatives
from ckeditor_uploader.fields import RichTextUploadingField
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
        """Get the Alert classes that target sites"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS['site']

    @classmethod
    def agency_alerts(cls):
        """Get the Alert classes that target agencies"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS['agency']

    @classmethod
    def user_alerts(cls):
        """Get the Alert classes that target users"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS['user']

    @classmethod
    def untargeted_alerts(cls):
        """Get the Alert classes that target all users"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS['untargeted']

    def from_signal(self, **kwargs):
        """
        Automated alerts must implement from_signal() to check for and create
        alerts based off supported triggering signals. The list of supported
        signals must be set in the Alert's manager SUPPORTED_SIGNALS class
        field.

        :param kwargs: The signal kwargs
        :return:
        """
        raise NotImplementedError(
            f'{self.__class__} must implement from_signal() to trigger alerts '
            f'from a signal.'
        )

    def classes(self):
        """
        Get all registered Alert classes of this type.
        :return:
        """
        from django.apps import apps
        classes = set()
        for app_config in apps.get_app_configs():
            for mdl in app_config.get_models():
                if issubclass(mdl, self.model):
                    classes.add(mdl)
        return classes

    def create(self, **kwargs):
        kwargs.setdefault('priority', getattr(self, 'DEFAULT_PRIORITY', 0))
        return super().create(**kwargs)


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

    def send_emails(self, request=None):
        for alert in self:
            alert.get_real_instance().send(request)


class Alert(PolymorphicModel):

    # automated alert types are only issued by the system
    automated = False

    template_txt = 'slm/emails/alert_issued.txt'
    template_html = 'slm/emails/alert_issued.html'

    logger = getLogger()

    DEFAULT_PRIORITY = 1

    @property
    def context(self):
        """Get the template render context for this alert"""
        return {
            'alert': self
        }

    @property
    def target(self):
        """Return the targeted object if any"""
        real = self.get_real_instance()
        if real == self:
            return None
        return real.target

    @property
    def untargeted(self):
        """Return true if this alert is for all users"""
        return (
            self.get_real_instance().__class__ in
            Alert.objects.untargeted_alerts()
        )

    @property
    def agency_alert(self):
        """Return true if this alert is for an Agency"""
        return (
            self.get_real_instance().__class__ in
            Alert.objects.agency_alerts()
        )

    @property
    def site_alert(self):
        """Return true if this alert is for a Site"""
        return (
            self.get_real_instance().__class__ in
            Alert.objects.site_alerts()
        )

    @property
    def user_alert(self):
        """Return true if this alert is for a User"""
        return (
            self.get_real_instance().__class__ in
            Alert.objects.user_alerts()
        )

    @property
    def users(self):
        """
        Return a queryset that contains all targeted users and any relevant
        moderators that may be interested in the alert.

        :return: User QuerySet
        """
        from django.contrib.auth import get_user_model
        if self.untargeted:
            return get_user_model().objects.all()
        if self.agency_alert:
            return get_user_model().objects.filter(agencies__in=[self.agency])
        if self.site_alert:
            return get_user_model().objects.filter(Q(pk__in=self.site.editors))
        if self.user_alert:
            return get_user_model().objects.filter(pk=self.user.pk)
        raise RuntimeError(
            f'Unable to determine targeted users for alert: {self}'
        )

    issuer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        help_text=_('The issuing user (if any).')
    )

    header = models.CharField(
        max_length=50,
        null=False,
        default='',
        help_text=_('A short description of the alert.')
    )
    detail = RichTextUploadingField(
        blank=True,
        null=False,
        default='',
        help_text=_('Longer description containing details of the alert.')
    )

    level = EnumField(
        AlertLevel,
        null=False,
        blank=False,
        db_index=True,
        help_text=_('The severity level of this alert.')
    )

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

    priority = models.IntegerField(
        default=0,
        blank=True,
        help_text=_(
            'The priority ordering for this alert. Alerts are shown by '
            'decreasing priority order first then by decreasing timestamp '
            'order.'
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

    def send(self, request=None):
        """
        Send an email to all targeted recipients about this alert. Targeted
        recipients are direct recipients, untargeted administrators are CCed.
        If this is an untargeted alert for all users the recipient list is
        BCCed.

        :return: True if the email was sent successfully - false otherwise
        """
        from django.contrib.auth import get_user_model
        text = get_template(self.template_txt)
        html = get_template(self.template_html)
        html_ok = self.untargeted or (
            not (self.users.emails_ok(html=False).count())
        )

        context = self.context
        context.update({
            'request': request,
            'current_site': DjangoSite.objects.get_current()
        })

        try:
            to, cc, bcc, bcc_text = set(), set(), set(), set()

            if self.untargeted:
                bcc = {
                    user.email for user in self.users.emails_ok(html=True)
                }
                bcc_text = {
                    user.email for user in self.users.emails_ok(html=False)
                }
            else:
                to = {user.email for user in self.users.emails_ok()}
                cc = {
                    user.email
                    for user in get_user_model().objects.filter(
                        is_superuser=True
                    )
                    if user not in bcc and user not in to
                }

            email_kwargs = {
                'subject': f'[{DjangoSite.objects.get_current().name}] {self}',
                'body': text.render(context),
                'from_email': from_email(),
                'to': to,
                'cc': cc,
                'bcc': bcc
            }
            email = EmailMultiAlternatives(**email_kwargs)
            if html_ok:
                email.attach_alternative(
                    html.render(context),
                    'text/html'
                )
            email.send(fail_silently=False)
            if bcc_text:
                EmailMultiAlternatives(
                    **{
                        **email_kwargs,
                        'bcc': bcc_text
                    }
                ).send(fail_silently=False)
            return True
        except (SMTPException, ConnectionError) as exc:
            self.logger.exception(exc)
            return False

    def __str__(self):
        if self.target:
            return f'[{self.target}] {self.header}'
        return self.header

    class Meta:
        ordering = ('-priority', '-timestamp',)
        verbose_name_plural = 'Alerts'


class SiteAlert(Alert):

    DEFAULT_PRIORITY = 2

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

    DEFAULT_PRIORITY = 4

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

    DEFAULT_PRIORITY = 3

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
    DEFAULT_PRIORITY = 0

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

    # eliminate conflict between Alert.timestamp and SiteFile.timestamp
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
        self.sticky = True
        self.expires = None
        self.send_email = False
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('site',)
        verbose_name_plural = 'GeodesyML Alerts'
