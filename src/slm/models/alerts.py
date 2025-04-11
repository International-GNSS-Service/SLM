import os
from logging import getLogger
from smtplib import SMTPException

from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site as DjangoSite
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.db.models import Q
from django.template.loader import get_template
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django_enum import EnumField
from polymorphic.managers import PolymorphicManager, PolymorphicQuerySet
from polymorphic.models import PolymorphicModel

from slm import signals as slm_signals
from slm.defines import AlertLevel, GeodesyMLVersion, SiteLogFormat, SLMFileType
from slm.models.system import SiteFile
from slm.parsing.xsd import SiteLogParser
from slm.utils import from_email


class AlertManager(PolymorphicManager):
    ALERT_MODELS = {}

    # automated alerts should set this set to this list of signals
    # that may trigger the alert
    SUPPORTED_SIGNALS = {"issue": {}, "rescind": {}}

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
        from django.contrib.auth import get_user_model
        from django.core.exceptions import FieldDoesNotExist

        from slm.models import Agency, Site

        cls.ALERT_MODELS = {
            "untargeted": set(),
            "site": set(),
            "agency": set(),
            "user": set(),
        }
        relations = [
            {"model": Site, "field": "site"},
            {"model": Agency, "field": "agency"},
            {"model": get_user_model(), "field": "user"},
        ]
        for app in apps.get_app_configs():
            for model in app.get_models():
                if issubclass(model, Alert):
                    found_relation = False
                    for relation in relations:
                        try:
                            if issubclass(
                                model._meta.get_field(relation["field"]).related_model,
                                relation["model"],
                            ):
                                found_relation = True
                                cls.ALERT_MODELS[relation["field"]].add(model)
                        except FieldDoesNotExist:
                            continue
                    if not found_relation:
                        cls.ALERT_MODELS["untargeted"].add(model)

    @classmethod
    def site_alerts(cls):
        """Get the Alert classes that target sites"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS["site"]

    @classmethod
    def agency_alerts(cls):
        """Get the Alert classes that target agencies"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS["agency"]

    @classmethod
    def user_alerts(cls):
        """Get the Alert classes that target users"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS["user"]

    @classmethod
    def untargeted_alerts(cls):
        """Get the Alert classes that target all users"""
        cls._init_alert_models_()
        return cls.ALERT_MODELS["untargeted"]

    def issue_from_signal(self, **kwargs):
        """
        Automated alerts must implement issue_from_signal() to check for and
        create alerts based off supported triggering signals. The list of
        supported signals must be set in the Alert's manager SUPPORTED_SIGNALS
        class field.

        :param kwargs: The signal kwargs
        :return:
        """
        raise NotImplementedError(
            f"{self.__class__} must implement issue_from_signal() to trigger "
            f"alerts from a signal."
        )

    def check_issue_signal_supported(self, signal):
        if signal not in self.SUPPORTED_SIGNALS["issue"]:
            from pprint import pformat

            from slm.signals import signal_name as name

            names = [name(sig) for sig in self.SUPPORTED_SIGNALS["issue"]]
            raise ImproperlyConfigured(
                f"{self.model.__name__} alert was triggered by {name(signal)} "
                f"which is not a supported issue signal:"
                f"\n{pformat(names, indent=4)}"
            )

    def check_rescind_signal_supported(self, signal):
        if signal not in self.SUPPORTED_SIGNALS["rescind"]:
            from pprint import pformat

            from slm.signals import signal_name as name

            names = [name(sig) for sig in self.SUPPORTED_SIGNALS["rescind"]]
            raise ImproperlyConfigured(
                f"{self.model.__name__} alert was rescinded by {name(signal)} "
                f"which is not a supported rescind signal:"
                f"\n{pformat(names, indent=4)}"
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
        kwargs.setdefault("priority", getattr(self, "DEFAULT_PRIORITY", 0))
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
        search = "" if isinstance(user, get_user_model()) else "__in"
        for alert_class in AlertManager.user_alerts():
            qry |= Q(**{f"{alert_class._meta.model_name}__user{search}": user})
        return qry

    @classmethod
    def sites_q(cls, sites):
        qry = Q()
        for alert_class in AlertManager.site_alerts():
            qry |= Q(**{f"{alert_class._meta.model_name}__site__in": sites})
        return qry

    @classmethod
    def site_q(cls, sites):
        qry = Q()
        for alert_class in AlertManager.site_alerts():
            qry |= Q(**{f"{alert_class._meta.model_name}__site": sites})
        return qry

    @classmethod
    def agencies_q(cls, agencies):
        qry = Q()
        for alert_class in AlertManager.agency_alerts():
            qry |= Q(**{f"{alert_class._meta.model_name}__agency__in": agencies})
        return qry

    @classmethod
    def untargeted_q(cls):
        qry = Q()
        for alert_class in AlertManager.untargeted_alerts():
            qry |= Q(polymorphic_ctype=ContentType.objects.get_for_model(alert_class))
        return qry

    def visible_to(self, user):
        """
        Return a queryset of Alerts that should be visible to the given user.
        For super users this is all alerts and for everyone else this is any
        untargeted alert as well as any alert targeted at them, any agencies
        they belong to, or any sites belonging to any agencies they belong to.

        :param user: The user to fetch alerts for
        :return:
        """
        from slm.models import Site

        if user.is_authenticated:
            if user.is_superuser:
                return self.all()
            else:
                return self.filter(
                    self.untargeted_q()
                    | self.user_q(user)
                    | self.sites_q(Site.objects.editable_by(user))
                    | self.agencies_q(user.agencies.all())
                )
        return self.none()

    def concerning_agencies(self, agencies):
        """
        Given an iterable of agencies return all Alerts that may be relevant.
        This includes all untargeted alerts, any alerts for the specific
        agencies and any alerts for users belonging to representing agencies or
        any users belonging to the represented agencies.
        """
        from slm.models import Site

        return self.filter(
            self.untargeted_q()
            | self.user_q(get_user_model().objects.filter(agencies__in=agencies))
            | self.sites_q(Site.objects.filter(agencies__in=agencies).distinct())
            | self.agencies_q(agencies)
        )

    def concerning_sites(self, sites):
        """
        Given an iterable of sites return all Alerts that may be relevant.
        This includes all untargeted alerts, any alerts for the specific sites
        and any alerts for users belonging to representing agencies or directly
        for represented agencies.
        """
        from slm.models import Agency

        agencies = Agency.objects.filter(sites__in=sites).distinct()
        ret = self.filter(
            self.untargeted_q()
            | self.user_q(
                get_user_model().objects.filter(agencies__in=agencies).distinct()
            )
            | self.sites_q(sites)
            | self.agencies_q(agencies)
        )
        return ret

    def send_emails(self, request=None):
        for alert in self:
            alert.get_real_instance().send(request)


class Alert(PolymorphicModel):
    # automated alert types are only issued by the system
    automated = False

    template_txt = "slm/emails/alert_issued.txt"
    template_html = "slm/emails/alert_issued.html"

    logger = getLogger()

    DEFAULT_PRIORITY = 1

    @property
    def context(self):
        """Get the template render context for this alert"""
        return {"alert": self}

    @property
    def target(self):
        """Return the targeted object if any"""
        real = self.get_real_instance()
        if real == self:
            return None
        return real.target

    @property
    def target_link(self):
        if self.site_alert:
            return reverse("slm:edit", kwargs={"station": self.target.name})
        elif self.agency_alert:
            return f"{reverse('slm:home')}?agency={self.target.pk}"
        elif self.user_alert:
            return f"mailto:{self.target.email}"
        return reverse("slm:alert", kwargs={"alert": self.pk})

    @property
    def untargeted(self):
        """Return true if this alert is for all users"""
        return self.get_real_instance().__class__ in Alert.objects.untargeted_alerts()

    @property
    def agency_alert(self):
        """Return true if this alert is for an Agency"""
        return self.get_real_instance().__class__ in Alert.objects.agency_alerts()

    @property
    def site_alert(self):
        """Return true if this alert is for a Site"""
        return self.get_real_instance().__class__ in Alert.objects.site_alerts()

    @property
    def user_alert(self):
        """Return true if this alert is for a User"""
        return self.get_real_instance().__class__ in Alert.objects.user_alerts()

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
        raise RuntimeError(f"Unable to determine targeted users for alert: {self}")

    issuer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        help_text=_("The issuing user (if any)."),
    )

    header = models.CharField(
        max_length=50,
        null=False,
        default="",
        help_text=_("A short description of the alert."),
    )
    detail = RichTextUploadingField(
        blank=True,
        null=False,
        default="",
        help_text=_("Longer description containing details of the alert."),
    )

    level = EnumField(
        AlertLevel,
        null=False,
        blank=False,
        db_index=True,
        help_text=_("The severity level of this alert."),
    )

    timestamp = models.DateTimeField(
        auto_now_add=True, help_text=_("The time the alert was created."), db_index=True
    )

    sticky = models.BooleanField(
        default=False,
        blank=True,
        help_text=_(
            "Do not allow target users to clear this alert, only admins may clear."
        ),
    )

    priority = models.IntegerField(
        default=0,
        blank=True,
        help_text=_(
            "The priority ordering for this alert. Alerts are shown by "
            "decreasing priority order first then by decreasing timestamp "
            "order."
        ),
        db_index=True,
    )

    expires = models.DateTimeField(
        null=True,
        default=None,
        blank=True,
        help_text=_("Automatically remove this alert after this time."),
        db_index=True,
    )

    send_email = models.BooleanField(
        default=False,
        null=False,
        blank=False,
        help_text=_(
            "If true, an email will be sent for this alert to every targeted user."
        ),
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
        html_ok = bool(self.untargeted or (self.users.emails_ok(html=True).count()))

        context = self.context
        context.update(
            {"request": request, "current_site": DjangoSite.objects.get_current()}
        )

        try:
            to, cc, bcc, bcc_text = set(), set(), set(), set()

            if self.untargeted:
                bcc = {user.email for user in self.users.emails_ok(html=True)}
                bcc_text = {user.email for user in self.users.emails_ok(html=False)}
            else:
                to = {user.email for user in self.users.emails_ok()}
                cc = {
                    user.email
                    for user in get_user_model()
                    .objects.emails_ok()
                    .filter(is_superuser=True)
                    if user not in bcc and user not in to
                }

            email_kwargs = {
                "subject": f"[{DjangoSite.objects.get_current().name}] {self}",
                "body": text.render(context),
                "from_email": from_email(),
                "to": to,
                "cc": cc,
                "bcc": bcc,
            }
            email = EmailMultiAlternatives(**email_kwargs)
            if html_ok:
                email.attach_alternative(html.render(context), "text/html")
            email.send(fail_silently=False)
            if bcc_text:
                EmailMultiAlternatives(**{**email_kwargs, "bcc": bcc_text}).send(
                    fail_silently=False
                )
            return True
        except (SMTPException, ConnectionError) as exc:
            self.logger.exception(exc)
            return False

    def __str__(self):
        if self.target:
            return f"({self.target}) {self.header}"
        return self.header

    class Meta:
        ordering = (
            "-priority",
            "-timestamp",
        )
        verbose_name_plural = " Alerts"
        verbose_name = "Alerts"


class SiteAlert(Alert):
    DEFAULT_PRIORITY = 2

    site = models.ForeignKey(
        "slm.Site",
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Only users with access to this site will see this alert."),
        related_name="alerts",
    )

    @property
    def target(self):
        return self.site

    def __str__(self):
        if self.site:
            return f"{self.site.name}: {super().__str__()}"
        return super().__str__()

    class Meta:
        verbose_name_plural = " Alerts: Site"
        verbose_name = "Site Alert"


class UserAlert(Alert):
    DEFAULT_PRIORITY = 4

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Only this user will see this alert."),
        related_name="alerts",
    )

    @property
    def target(self):
        return self.user

    class Meta:
        verbose_name_plural = " Alerts: User"
        verbose_name = "User Alert"


class ImportAlert(Alert):
    """
    An alert reserved for issue when issues arise during import of data
    into the system.
    """

    DEFAULT_PRIORITY = 1

    site = models.OneToOneField(
        "slm.Site",
        on_delete=models.CASCADE,
        help_text=_("Only users with access to this site will see this alert."),
        related_name="import_alert",
        null=False,
    )

    file_contents = models.TextField(
        blank=True,
        default="",
        help_text=_(
            "The text contents of the file that import was attempted from (if applicable)."
        ),
    )

    findings = models.JSONField(null=True, default=None)

    log_format = EnumField(SiteLogFormat, null=True, default=None)

    @property
    def context(self):
        return {
            **super().context,
            "findings": self.findings,
            "site": self.site,
            "file": self.file_contents,
            "upload_tmpl": self.upload_tmpl,
        }

    @property
    def target(self):
        return self.site

    @property
    def upload_tmpl(self):
        if self.log_format:
            if self.log_format in [SiteLogFormat.LEGACY, SiteLogFormat.ASCII_9CHAR]:
                return "slm/station/uploads/legacy.html"
            elif self.log_format is SiteLogFormat.GEODESY_ML:
                return "slm/station/uploads/geodesyml.html"
            elif self.log_format is SiteLogFormat.JSON:
                return "slm/station/uploads/json.html"
        return None

    def __str__(self):
        if self.site:
            return f"{self.site.name}: {super().__str__()}"
        return super().__str__()

    class Meta:
        verbose_name_plural = " Alerts: Import"
        verbose_name = "Import Alert"


class AgencyAlert(Alert):
    DEFAULT_PRIORITY = 3

    agency = models.ForeignKey(
        "slm.Agency",
        null=True,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Only members of this agency will see this alert."),
        related_name="alerts",
    )

    @property
    def target(self):
        return self.agency

    class Meta:
        verbose_name_plural = " Alerts: Agency"
        verbose_name = "Agency Alert"


class AutomatedAlertMixin:
    automated = True

    def save(self, *args, **kwargs):
        for key, val in (
            getattr(settings, "SLM_AUTOMATED_ALERTS", {})
            .get(self._meta.label, {})
            .items()
        ):
            if key in {"issue", "rescind"}:
                continue
            if callable(val):
                val = val()
            setattr(self, key, val)
        super().save(*args, **kwargs)


class GeodesyMLInvalidManager(AlertManager):
    SUPPORTED_SIGNALS = {
        "issue": {
            slm_signals.site_published,
            slm_signals.site_status_changed,
            slm_signals.section_added,
            slm_signals.section_edited,
            slm_signals.section_deleted,
            slm_signals.site_file_published,
            slm_signals.site_file_unpublished,
        }
    }

    def issue_from_signal(self, signal, site=None, **kwargs):
        """
        Check if an alert should be issued when the given signal is dispatched
        and issue the alert if necessary.

        :param signal:
        :param site:
        :param kwargs:
        :return: The alert that was issued if
        """
        self.check_issue_signal_supported(signal)
        site.refresh_from_db()
        return self.check_site(
            site=site,
            published=(
                True
                if signal
                in {
                    slm_signals.site_published,
                    slm_signals.site_file_published,
                    slm_signals.site_file_unpublished,
                }
                else None
            ),
        )

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

        if hasattr(site, "geodesymlinvalid") and site.geodesymlinvalid:
            if os.path.exists(site.geodesymlinvalid.file.path):
                os.remove(site.geodesymlinvalid.file.path)
            site.geodesymlinvalid.delete()

        geo_version = GeodesyMLVersion.latest()
        serializer = SiteLogSerializer(instance=site, published=published)
        xml_str = serializer.format(SiteLogFormat.GEODESY_ML, version=geo_version)
        parser = SiteLogParser(xml_str, site_name=site.name)
        if parser.errors:
            xml_file = ContentFile(
                xml_str.encode("utf-8"),
                name=site.get_filename(log_format=SiteLogFormat.GEODESY_ML),
            )
            obj = self.model.objects.create(
                published=serializer.is_published,
                site=site,
                schema=geo_version,
                findings={
                    lineno: (err.level, err.message)
                    for lineno, err in parser.errors.items()
                },
                file=xml_file,
            )
            return obj
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
            if GeodesyMLInvalidManager.objects.check_site(site, published=published):
                alerts += 1
        return alerts


class GeodesyMLInvalid(AutomatedAlertMixin, SiteFile, Alert):
    SUB_DIRECTORY = "alerts"
    DEFAULT_PRIORITY = 0

    @property
    def context(self):
        return {
            **super().context,
            "findings": self.findings,
            "site": self.site,
            "file": self,
        }

    @property
    def target(self):
        return self.site

    # eliminate conflict between Alert.timestamp and SiteFile.timestamp
    timestamp = Alert.timestamp

    site = models.OneToOneField(
        "slm.Site",
        null=False,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("The site this alert applies to."),
        related_name="geodesymlinvalid",
    )

    findings = models.JSONField()

    schema = EnumField(
        GeodesyMLVersion,
        null=False,
        default=GeodesyMLVersion.latest(),
        help_text=_("The schema version that failed validation."),
    )

    published = models.BooleanField(
        null=False,
        help_text=_(
            "True if this alert was issued from the published version of the site log."
        ),
    )

    objects = GeodesyMLInvalidManager.from_queryset(GeodesyMLInvalidQuerySet)()

    def save(self, *args, **kwargs):
        self.mimetype = SiteLogFormat.GEODESY_ML.mimetype
        self.file_type = SLMFileType.SITE_LOG
        self.log_format = SiteLogFormat.GEODESY_ML
        self.header = _("GeodesyML is Invalid.")
        self.detail = _(
            "The data for this site does not validate against GeodesyML "
            "schema version: "
        ) + str(self.schema)
        self.sticky = True
        self.expires = None
        self.send_email = False
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("site",)
        verbose_name_plural = " Alerts: GeodesyML Invalid"
        verbose_name = "GeodesyML Invalid"


class ReviewRequestedManager(AlertManager):
    SUPPORTED_SIGNALS = {
        "issue": {
            slm_signals.review_requested,
            slm_signals.section_added,
            slm_signals.section_edited,
            slm_signals.section_deleted,
            slm_signals.site_file_uploaded,
            slm_signals.site_file_unpublished,
            slm_signals.site_proposed,
        },
        "rescind": {
            slm_signals.updates_rejected,
            slm_signals.site_published,
            slm_signals.site_file_published,
            slm_signals.section_added,
            slm_signals.section_edited,
            slm_signals.section_deleted,
        },
    }

    def issue_from_signal(self, signal, site=None, **kwargs):
        self.check_issue_signal_supported(signal)
        if site:
            if hasattr(site, "review_requested") and site.review_requested:
                site.review_requested.timestamp = now()
                site.review_requested.save()
            else:
                return self.create(
                    site=site,
                    issuer=getattr(kwargs.get("request", None), "user", None),
                    detail=kwargs.get("detail", "") or "",
                )

    def rescind_from_signal(self, signal, site=None, **kwargs):
        self.check_rescind_signal_supported(signal)
        if site:
            return self.filter(site=site).delete()


class ReviewRequestedQueryset(AlertQuerySet):
    pass


class ReviewRequested(AutomatedAlertMixin, Alert):
    DEFAULT_PRIORITY = 0

    @property
    def target_link(self):
        return reverse("slm:review", kwargs={"station": self.target.name})

    @property
    def context(self):
        return {**super().context, "site": self.site}

    @property
    def target(self):
        return self.site

    @property
    def requester(self):
        return self.issuer

    site = models.OneToOneField(
        "slm.Site",
        null=False,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("The site this alert applies to."),
        related_name="review_requested",
    )

    objects = ReviewRequestedManager.from_queryset(ReviewRequestedQueryset)()

    def save(self, *args, **kwargs):
        self.header = _("Review Requested.")
        self.sticky = False
        self.expires = None
        self.send_email = True
        self.level = AlertLevel.NOTICE
        if not self.detail:
            self.detail = (
                _(
                    '<a href="mailto:{}">{}</a> has requested the updates to '
                    "this site log be published."
                ).format(self.requester.email, self.requester.name)
                if self.requester
                else _(
                    "A request has been made to publish the updates to this site log."
                )
            )
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("site",)
        verbose_name_plural = " Alerts: Review Requested"
        verbose_name = "Review Requested"


class UnpublishedFilesAlertManager(AlertManager):
    SUPPORTED_SIGNALS = {
        "issue": {slm_signals.site_file_uploaded, slm_signals.site_file_unpublished},
        "rescind": {slm_signals.site_file_published, slm_signals.site_file_deleted},
    }

    def issue_from_signal(self, signal, site=None, **kwargs):
        from slm.defines import SiteFileUploadStatus, SLMFileType
        from slm.models import SiteFileUpload

        self.check_issue_signal_supported(signal)
        if site:
            if (
                hasattr(site, "unpublished_files_alert")
                and site.unpublished_files_alert
            ):
                site.unpublished_files_alert.timestamp = now()
                site.unpublished_files_alert.save()
            elif SiteFileUpload.objects.filter(
                Q(site=site)
                & ~Q(file_type=SLMFileType.SITE_LOG)
                & Q(status=SiteFileUploadStatus.UNPUBLISHED)
            ).exists():
                with transaction.atomic():
                    return self.update_or_create(
                        site=site,
                        defaults={
                            "issuer": getattr(
                                kwargs.get("request", None), "user", None
                            ),
                            "detail": kwargs.get("detail", "") or "",
                        },
                    )[0]

    def rescind_from_signal(self, signal, site=None, **kwargs):
        from slm.defines import SiteFileUploadStatus, SLMFileType
        from slm.models import SiteFileUpload

        self.check_rescind_signal_supported(signal)
        if site:
            if (
                hasattr(site, "unpublished_files_alert")
                and site.unpublished_files_alert
                and not SiteFileUpload.objects.filter(
                    Q(site=site)
                    & ~Q(file_type=SLMFileType.SITE_LOG)
                    & Q(status=SiteFileUploadStatus.UNPUBLISHED)
                ).exists()
            ):
                return self.filter(site=site).delete()


class UnpublishedFilesAlertQueryset(AlertQuerySet):
    pass


class UnpublishedFilesAlert(AutomatedAlertMixin, Alert):
    DEFAULT_PRIORITY = 0

    @property
    def target_link(self):
        return reverse("slm:upload", kwargs={"station": self.target.name})

    @property
    def context(self):
        return {**super().context, "site": self.site}

    @property
    def target(self):
        return self.site

    site = models.OneToOneField(
        "slm.Site",
        null=False,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("The site this alert applies to."),
        related_name="unpublished_files_alert",
    )

    objects = UnpublishedFilesAlertManager.from_queryset(
        UnpublishedFilesAlertQueryset
    )()

    def save(self, *args, **kwargs):
        self.header = _("Unpublished Files")
        self.sticky = True
        self.expires = None
        self.send_email = True
        self.level = AlertLevel.NOTICE
        if not self.detail:
            self.detail = _("This site has unpublished files.")
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("site",)
        verbose_name_plural = " Alerts: Unpublished Files"
        verbose_name = "Unpublished Files"


class SiteLogPublishedManager(AlertManager):
    SUPPORTED_SIGNALS = {"issue": {slm_signals.site_published}}

    def issue_from_signal(self, signal, site=None, **kwargs):
        with transaction.atomic():
            return self.update_or_create(
                site=site,
                defaults={
                    "issuer": getattr(kwargs.get("request", None), "user", None),
                    "detail": kwargs.get("detail", "") or "",
                },
            )[0]


class SiteLogPublishedQueryset(AlertQuerySet):
    pass


class SiteLogPublished(AutomatedAlertMixin, Alert):
    DEFAULT_PRIORITY = 0

    @property
    def target_link(self):
        return reverse("slm:download", kwargs={"station": self.target.name})

    @property
    def context(self):
        return {**super().context, "site": self.site}

    @property
    def target(self):
        return self.site

    site = models.OneToOneField(
        "slm.Site",
        null=False,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("The site this alert applies to."),
        related_name="published_alerts",
    )

    objects = SiteLogPublishedManager.from_queryset(SiteLogPublishedQueryset)()

    def save(self, *args, **kwargs):
        from slm.templatetags.slm import file_url

        self.header = _("Log Published")
        self.sticky = False
        # by default expire these alerts immediately - this will mean any
        # configured emails will go out but the alert will never be visible
        # in the system interface
        self.expires = self.expires or now()
        self.send_email = True
        self.level = AlertLevel.NOTICE
        if not self.detail:
            legacy_link = file_url(
                reverse(
                    "slm_public_api:download-detail",
                    kwargs={"site": self.site.name, "format": "log"},
                )
            )
            gml_link = file_url(
                reverse(
                    "slm_public_api:download-detail",
                    kwargs={"site": self.site.name, "format": "xml"},
                )
            )
            self.detail = _(
                "An updated log has been published for this site. Download "
                "the new {legacy_file} or the new {geodesyml_file}."
            ).format(
                legacy_file=f'<a href="{legacy_link}" download>{_("legacy file")}</a>',
                geodesyml_file=f'<a href="{gml_link}" download>'
                f"{_('GeodesyML file')}</a>",
            )
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("site",)
        verbose_name_plural = " Alerts: Log Published"
        verbose_name = "Log Published"


class UpdatesRejectedManager(AlertManager):
    SUPPORTED_SIGNALS = {
        "issue": {slm_signals.updates_rejected},
        "rescind": {
            slm_signals.site_published,
            slm_signals.site_file_published,
            slm_signals.review_requested,
            slm_signals.section_added,
            slm_signals.section_edited,
            slm_signals.section_deleted,
        },
    }

    def issue_from_signal(self, signal, site=None, **kwargs):
        self.check_issue_signal_supported(signal)
        if site:
            if hasattr(site, "updates_rejected") and site.updates_rejected:
                site.updates_rejected.timestamp = now()
                site.updates_rejected.save()
            else:
                return self.create(
                    site=site,
                    issuer=getattr(kwargs.get("request", None), "user", None),
                    detail=kwargs.get("detail", "") or "",
                )

    def rescind_from_signal(self, signal, site=None, **kwargs):
        self.check_rescind_signal_supported(signal)
        if site:
            return self.filter(site=site).delete()


class UpdatesRejectedQueryset(AlertQuerySet):
    pass


class UpdatesRejected(AutomatedAlertMixin, Alert):
    DEFAULT_PRIORITY = 0

    @property
    def target_link(self):
        return reverse("slm:alerts", kwargs={"station": self.target.name})

    @property
    def context(self):
        return {**super().context, "site": self.site}

    @property
    def target(self):
        return self.site

    @property
    def rejecter(self):
        return self.issuer

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_NULL,
    )

    site = models.OneToOneField(
        "slm.Site",
        null=False,
        default=None,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("The site this alert applies to."),
        related_name="updates_rejected",
    )

    objects = UpdatesRejectedManager.from_queryset(UpdatesRejectedQueryset)()

    def save(self, *args, **kwargs):
        self.header = _("Updates were rejected.")
        self.sticky = False
        self.expires = None
        self.send_email = True
        self.level = AlertLevel.ERROR
        if not self.detail:
            self.detail = (
                _('Updates were rejected by <a href="mailto:{}">{}</a>').format(
                    self.rejecter.email, self.rejecter.name
                )
                if self.rejecter
                else _("Updates were rejected.")
            )
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("site",)
        verbose_name_plural = " Alerts: Updates Rejected"
        verbose_name = "Updates Rejected"
