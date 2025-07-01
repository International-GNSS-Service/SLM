"""
Handles web requests and responses.

NOTES:
Holds important functions for each page.
Data processing, validation, etc. lives here.

ADD MORE COMMENTS

MORE INFO:
https://docs.djangoproject.com/en/stable/topics/http/views/
"""

from enum import Enum

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Max, Q
from django.db.models.fields import NOT_PROVIDED
from django.http import Http404, HttpResponseNotFound
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from slm import defines
from slm.api.edit.views import StationFilterForm
from slm.defines import (
    AlertLevel,
    SiteFileUploadStatus,
    SiteLogFormat,
    SiteLogStatus,
    SLMFileType,
)
from slm.forms import (
    NewSiteForm,
    RichTextForm,
    SiteAntennaForm,
    SiteCollocationForm,
    SiteFileForm,
    SiteFormForm,
    SiteFrequencyStandardForm,
    SiteHumiditySensorForm,
    SiteIdentificationForm,
    SiteLocalEpisodicEffectsForm,
    SiteLocationForm,
    SiteMoreInformationForm,
    SiteMultiPathSourcesForm,
    SiteOperationalContactForm,
    SiteOtherInstrumentationForm,
    SitePressureSensorForm,
    SiteRadioInterferencesForm,
    SiteReceiverForm,
    SiteResponsibleAgencyForm,
    SiteSignalObstructionsForm,
    SiteSurveyedLocalTiesForm,
    SiteTemperatureSensorForm,
    SiteWaterVaporRadiometerForm,
    UserForm,
    UserProfileForm,
)
from slm.models import (
    About,
    Agency,
    Alert,
    ArchivedSiteLog,
    Help,
    Network,
    Site,
    SiteFileUpload,
    SiteLocation,
    SiteSubSection,
)
from slm.parsing import Error, Warn

User = get_user_model()


@method_decorator(login_required, name="dispatch")
class SLMView(TemplateView):
    DEFINES = {
        name: define
        for name, define in vars(defines).items()
        if isinstance(define, type) and issubclass(define, Enum)
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.DEFINES)
        Alert.objects.all().delete_expired()
        max_alert = Alert.objects.visible_to(self.request.user).aggregate(Max("level"))[
            "level__max"
        ]
        if max_alert is NOT_PROVIDED:
            max_alert = None

        context["user"] = self.request.user
        context["alert_level"] = AlertLevel(max_alert) if max_alert else None

        context["SLM_ORG_NAME"] = getattr(settings, "SLM_ORG_NAME", None)
        context["is_moderator"] = (
            self.request.user.is_superuser if self.request.user else None
        )
        context["networks"] = Network.objects.all()
        if self.request.user.is_superuser:
            context["user_agencies"] = Agency.objects.all()
        else:
            context["user_agencies"] = self.request.user.agencies.all()
        return context


class StationContextView(SLMView):
    station = None
    agencies = None
    sites = None
    site = None

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.station = kwargs.get("station", None)
        self.sites = Site.objects.editable_by(self.request.user)
        self.site = (
            Site.objects.filter(name__iexact=self.station)
            .editable_by(self.request.user)
            .first()
        )
        initial = None
        if self.request.GET:
            station_filter = StationFilterForm(data=self.request.GET)
            station_filter.full_clean()
            if station_filter.errors:
                raise Http404(station_filter.errors)
            initial = station_filter.cleaned_data
        filter_form = StationFilterForm(initial=initial)
        if self.site:
            self.agencies = [agency for agency in self.site.agencies.all()]
            location = SiteLocation.objects.filter(site=self.site).head()
            if location and location.llh:
                context["station_position"] = (location.llh[0], location.llh[1])
            context["attn_files"] = (
                self.site.sitefileuploads.available_to(self.request.user)
                .filter(status=SiteFileUploadStatus.UNPUBLISHED)
                .count()
            )
        else:
            self.agencies = filter_form.initial.get("agency", [])

        max_alert = (
            Alert.objects.visible_to(self.request.user)
            .for_site(self.site)
            .aggregate(Max("level"))["level__max"]
        )
        if max_alert is NOT_PROVIDED:
            max_alert = None

        context.update(
            {
                "num_sites": self.sites.count(),
                "station": self.station if self.station else None,
                "site": self.site if self.site else None,
                "agencies": self.agencies,
                "is_moderator": (
                    self.site.is_moderator(self.request.user) if self.site else None
                ),
                # some non-moderators may be able to publish a some changes
                "can_publish": (
                    self.site.can_publish(self.request.user) if self.site else None
                ),
                "is_publishable": self.site.is_publishable() if self.site else None,
                "link_view": (
                    "slm:edit"
                    if self.request.resolver_match.view_name
                    not in {
                        "slm:alerts",
                        "slm:download",
                        "slm:review",
                        "slm:log",
                        "slm:edit",
                    }
                    else self.request.resolver_match.view_name
                ),
                "station_alert_level": (AlertLevel(max_alert) if max_alert else None),
                "site_alerts": Alert.objects.site_alerts(),
                "filter_form": filter_form,
            }
        )

        if self.station:
            try:
                self.station = Site.objects.get(name=context["station"])
                if (
                    not self.request.user.is_superuser
                    and self.station not in self.sites
                ):
                    raise PermissionDenied()
            except Site.DoesNotExist:
                raise Http404(f"Site {context['station']} was not found!")
        return context


class EditView(StationContextView):
    """
    This is the view that creates and renders a context when a user requests
    to edit a site log. Site log edit forms do not render a giant form for the
    entire site log. The specific section being edited is part of the request
    url. So the job of this view is to compile enough context to render the
    status and error information for all sections as well as all of the
    information required to edit the requested section.
    """

    template_name = "slm/station/edit.html"

    FORMS = {
        form.Meta.model.section_slug(): form
        for form in [
            SiteFormForm,
            SiteIdentificationForm,
            SiteLocationForm,
            SiteReceiverForm,
            SiteAntennaForm,
            SiteSurveyedLocalTiesForm,
            SiteFrequencyStandardForm,
            SiteCollocationForm,
            SiteHumiditySensorForm,
            SitePressureSensorForm,
            SiteTemperatureSensorForm,
            SiteWaterVaporRadiometerForm,
            SiteOtherInstrumentationForm,
            SiteRadioInterferencesForm,
            SiteMultiPathSourcesForm,
            SiteSignalObstructionsForm,
            SiteLocalEpisodicEffectsForm,
            SiteOperationalContactForm,
            SiteResponsibleAgencyForm,
            SiteMoreInformationForm,
        ]
    }

    def get_context_data(self, **kwargs):
        """
        Builds a context that contains the sections and their meta information
        as well as forms bound ot the site log data at head for the section
        being edited. The context dictionary includes all StationContextView
        context as well as:

        ..code-block::

            # forms contains the information needed to render the forms in the
            # central edit pane
            'forms': [...],  # bound form instances to section models at head
                             # for the section being edited. If the section
                             # does not allow subsections it will be a list of
                             # length 1, if it does allow subections, it will
                             # be a list of bound subsection forms and the
                             # first instance in the list will be an unbound
                             # form used to add new subsections

            'multi': True,   # True if the section being edited has subsections
            'section_id': str,  # The identifier of the section being edited
            'section_name': str,  # The display name of the section

            # dictionary of sections in render-order - keys are section_names
            # this dictionary contains the meta information needed to render
            # the navigation
            'sections': {
                'Section Name': {
                    'flags': int,  # the cumulative number of error flags on
                                   # this section
                    'id': str,  # section_id

                     # the SiteLogStatus of the section
                    'status':  SiteLogStatus

                    'subsections': {
                        'Subsection Name': {
                            'active': False,  # True if subsection is selected
                            'flags': # the number of error flags the subsection
                            'id': str,  # section_id

                            # the SiteLogStatus of the section
                            'status': SiteLogStatus
                        },
                        ...
                    },
                },
                ...
            }

        """
        context = super().get_context_data(**kwargs)
        if not self.site:
            raise Http404(f"Station {kwargs.get('station', '')} does not exist!")
        context.update(
            {
                "section_id": kwargs.get("section", None),
                "sections": {},
                "forms": [],
                "station_images": self.site.sitefileuploads.available_to(
                    self.request.user
                ).filter(
                    status=SiteFileUploadStatus.PUBLISHED,
                    file_type=SLMFileType.SITE_IMAGE,
                ),
                "station_attachments": self.site.sitefileuploads.available_to(
                    self.request.user
                ).filter(
                    status=SiteFileUploadStatus.PUBLISHED,
                    file_type=SLMFileType.ATTACHMENT,
                ),
            }
        )

        section = self.FORMS.get(kwargs.get("section", None), None)
        if section:
            context["section_name"] = section.section_name()
            context["multi"] = issubclass(section._meta.model, SiteSubSection)

        # create the context of our form tree - the form/edit templates are
        # responsible for rendering this structure in html
        for section_id, form in self.FORMS.items():
            if hasattr(form, "NAV_HEADING"):
                context["sections"].setdefault(
                    form.NAV_HEADING,
                    {
                        "id": form.group_name(),
                        "flags": 0,
                        "status": SiteLogStatus.EMPTY,
                        "active": False,
                        "subsections": {},
                    },
                )["subsections"][form.section_name()] = {
                    "id": form.section_name().lower().replace(" ", ""),
                    "group": form.group_name(),  # todo remove
                    "parent": form.group_name(),
                    "flags": 0,
                    "active": False,
                    "status": SiteLogStatus.EMPTY,
                }
                if section is form:
                    context["parent"] = form.group_name()

            else:
                context["sections"][form.section_name()] = {
                    "id": form.section_name().lower().replace(" ", ""),
                    "flags": 0,
                    "status": SiteLogStatus.EMPTY,
                }

            if issubclass(form._meta.model, SiteSubSection):
                # for subsections we need to:
                #   1) set nav heading meta information
                #   2) add sections for all children
                #   3) populate the subsections of the requested edit form

                heading = context["sections"][
                    getattr(form, "NAV_HEADING", form.section_name())
                ]
                subheading = None
                if hasattr(form, "NAV_HEADING"):
                    subheading = heading["subsections"][form.section_name()]

                for inst in (
                    form._meta.model.objects.station(self.station)
                    .head(include_deleted=True)
                    .sort(reverse=True)
                ):
                    if section is form:
                        # if this is our requested form for editing - populate
                        # it with data from head
                        context["forms"].append(
                            form(
                                instance=inst,
                                initial={
                                    field: getattr(inst, field)
                                    for field in form._meta.fields
                                },
                            )
                        )

                    heading["flags"] += inst.num_flags if inst else 0
                    heading["status"] = heading.get("status", inst.mod_status).merge(
                        inst.mod_status
                    )
                    if subheading:
                        subheading.setdefault("flags", 0)
                        subheading["flags"] += inst.num_flags if inst else 0
                        subheading["status"] = subheading.get(
                            "status", inst.mod_status
                        ).merge(inst.mod_status)

                if section is form:
                    # if this is the edit section we add an empty form as the
                    # first form in the context, the template knows to render
                    # this form as the 'add' subsection form
                    context["forms"].insert(0, form(initial={"site": self.station}))
                    context["copy_last_on_add"] = [
                        field
                        for field in getattr(form, "COPY_LAST_ON_ADD", [])
                        if field not in {"id", "subsection"}
                        # guard against these ^ fields being included -
                        # will break things
                    ]
                    heading["active"] = heading.get("active", True) | True
                    if subheading:
                        subheading["active"] = True

                # add form (sub-sub section) numbers
                number = 1
                for form in reversed(context["forms"]):
                    if not getattr(form.instance, "is_deleted", False):
                        form.form_number = number
                        number += 1

            else:
                instance = form._meta.model.objects.station(
                    self.station
                ).head()  # we always edit on head
                if section is form:
                    # only one form is requested per edit view request - if
                    # this section is that form we need to populate it with
                    # data
                    context["forms"].append(
                        form(
                            instance=instance,
                            initial=(
                                {
                                    field: getattr(instance, field, None)
                                    for field in form._meta.fields
                                }
                                if instance
                                else {"site": self.station}
                            ),
                        )
                    )
                    context["sections"][form.section_name()]["active"] = True

                # for all sections we need to set status and number of flags
                context["sections"][form.section_name()]["flags"] = (
                    instance.num_flags if instance else 0
                )
                context["sections"][form.section_name()]["status"] = (
                    instance.mod_status if instance else SiteLogStatus.EMPTY
                )

        return context


class StationAlertsView(StationContextView):
    template_name = "slm/station/alerts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exclude_targets"] = True
        return context


class UploadView(StationContextView):
    template_name = "slm/station/upload.html"

    def get_context_data(self, file=None, **kwargs):
        context = super().get_context_data(**kwargs)
        if file:
            try:
                file = SiteFileUpload.objects.get(pk=file)
            except SiteFileUpload.DoesNotExist:
                raise Http404(f"File {file} does not exist.")
            context["file"] = file
            if file.context:
                context.update(file.context)
                if "findings" in context:
                    errors = 0
                    warnings = 0
                    for lineno, finding in context["findings"].items():
                        if finding[0] == Error.level:
                            errors += 1
                        elif finding[0] == Warn.level:
                            warnings += 1
                    context["finding_errors"] = errors
                    context["finding_warnings"] = warnings

            if file.file_type in {SLMFileType.SITE_IMAGE, SLMFileType.ATTACHMENT}:
                context["form"] = SiteFileForm(instance=file)
        context["num_files"] = SiteFileUpload.objects.filter(site=self.site).count()
        context["MAX_UPLOAD_MB"] = getattr(settings, "SLM_MAX_UPLOAD_SIZE_MB", 100)
        context["link_view"] = "slm:upload"
        return context


class NewSiteView(StationContextView):
    template_name = "slm/new_site.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = NewSiteForm(
            initial=(
                {"agencies": self.request.user.agencies.all()}
                if not self.request.user.is_superuser
                else {}
            )
        )
        if not self.request.user.is_superuser:
            context["form"].fields["agencies"].queryset = self.request.user.agencies
        return context


class IndexView(StationContextView):
    template_name = "slm/station/base.html"


class DownloadView(StationContextView):
    template_name = "slm/station/download.html"


class UserProfileView(SLMView):
    template_name = "slm/profile.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            {
                **self.get_context_data(**kwargs),
                "user_form": UserForm(instance=request.user),
                "profile_form": UserProfileForm(instance=request.user.profile),
            }
        )


class LogView(StationContextView):
    template_name = "slm/station/log.html"


class UserActivityLogView(SLMView):
    template_name = "slm/user_activity.html"

    def get_context_data(self, log_user=None, **kwargs):
        context = super().get_context_data()
        try:
            if log_user:
                # must be a super user to see other people's log history
                # todo configurable perm for this? like is mod for user's
                #  agency?
                if not self.request.user.is_superuser:
                    raise PermissionDenied()

                context["log_user"] = get_user_model().objects.get(pk=log_user)
            else:
                # otherwise we're getting the logged in user's log history
                context["log_user"] = self.request.user

        except get_user_model().DoesNotExist:
            raise Http404()

        return context


class StationReviewView(StationContextView):
    template_name = "slm/station/review.html"

    LOG_FORMATS = {
        fmt
        for fmt in SiteLogFormat
        if fmt not in {SiteLogFormat.JSON, SiteLogFormat.LEGACY}
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # we use legacy log files on the ascii 9 char review stack if no 9 char file is available
        review_stack = {fmt: [] for fmt in self.LOG_FORMATS}
        for fmt in self.LOG_FORMATS:
            fmt_q = Q(log_format=fmt)
            if fmt is SiteLogFormat.ASCII_9CHAR:
                fmt_q |= Q(log_format=SiteLogFormat.LEGACY)
            for archive in (
                ArchivedSiteLog.objects.filter(Q(site=self.site) & fmt_q)
                .order_by("-index__valid_range", "-log_format")
                .values_list("index__valid_range", "id")
                .distinct("index__valid_range")
            ):
                review_stack[fmt].append((archive[0].lower, archive[1]))
        ctx = {
            **ctx,
            "richtextform": RichTextForm(),
            "default_format": SiteLogFormat.ASCII_9CHAR,
            "log_formats": self.LOG_FORMATS,
            "review_stack": review_stack,
            "needs_publish": self.station.needs_publish(),
        }
        if ctx["needs_publish"]:
            for fmt in self.LOG_FORMATS:
                ctx["review_stack"][fmt].insert(0, (None, None))
        return ctx


class AlertsView(SLMView):
    template_name = "slm/alerts.html"


class AlertView(StationContextView):
    template_name = "slm/station/alert.html"
    template_map = {}
    alert = None

    def get_template(self, alert):
        if alert.__class__ not in self.template_map:
            try:
                self.template_map[alert.__class__] = get_template(
                    f"slm/alerts/{alert.__class__.__name__.lower()}.html"
                )
            except TemplateDoesNotExist:
                self.template_map[alert.__class__] = get_template(
                    "slm/alerts/alert.html"
                )
        return self.template_map[alert.__class__]

    def get_context_data(self, **kwargs):
        if hasattr(self.alert, "site") and self.alert.site:
            kwargs["station"] = self.alert.site.name
        context = super().get_context_data(**kwargs)
        context.update(
            {
                **self.alert.context,
                "alert_template": self.get_template(self.alert).origin.template_name,
                "exclude_targets": True,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        try:
            self.alert = Alert.objects.get(pk=kwargs.pop("alert", None))
        except Alert.DoesNotExist:
            return HttpResponseNotFound()
        return super().get(request, *args, **kwargs)


class HelpView(SLMView):
    template_name = "slm/help.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "help": Help.load()}


class AboutView(SLMView):
    template_name = "slm/about.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "about": About.load()}
