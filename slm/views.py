"""
Handles web requests and responses.

NOTES:
Holds important functions for each page.  
Data processing, validation, etc. lives here.

ADD MORE COMMENTS

MORE INFO:
https://docs.djangoproject.com/en/3.2/topics/http/views/
"""

from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.conf import settings
from slm.models import (
    Alert,
    Site,
    SiteSubSection,
    LogEntry,
    UserProfile,
    Agency,
    Network
)
from slm.defines import (
    SiteLogStatus,
    LogEntryType
)
from django.shortcuts import redirect
from datetime import datetime
from slm.utils import to_bool
from django.core.exceptions import PermissionDenied
from slm.api.serializers import SiteLogSerializer
from django.http import Http404
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from slm.defines import AlertLevel
from django.db.models.fields import NOT_PROVIDED
from django.db.models import (
    Max,
    Q
)
from slm.forms import (
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
    UserProfileForm,
    UserForm,
    NewSiteForm
)
from slm import signals as slm_signals

User = get_user_model()


class SLMView(TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_alert = Alert.objects.for_user(
            self.request.user
        ).aggregate(Max('level'))['level__max']
        if max_alert is NOT_PROVIDED:
            max_alert = None

        context['user'] = self.request.user
        context['SiteLogStatus'] = SiteLogStatus
        context['alert_level'] = AlertLevel(max_alert) if max_alert else None

        context['SLM_ORG_NAME'] = getattr(
            settings,
            'SLM_ORG_NAME',
            None
        )
        context['is_moderator'] = (
            self.request.user.is_superuser if self.request.user else None
        )
        context['networks'] = Network.objects.all()
        context['user_agencies'] = (
            Agency.objects.all()
            if self.request.user.is_superuser
            else Agency.objects.filter(pk=self.request.user.agency.pk)
        )
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
        self.station = kwargs.get('station', None)
        self.sites = Site.objects.editable_by(self.request.user)
        self.site = Site.objects.filter(name=self.station).first()
        if self.site:
            self.agencies = [
                agency.name for agency in self.site.agencies.all()
            ]

        max_alert = Alert.objects.for_user(
            self.request.user
        ).filter(site=self.site).aggregate(Max('level'))['level__max']
        if max_alert is NOT_PROVIDED:
            max_alert = None
        context.update({
            'num_sites': self.sites.count(),
            'station': self.station if self.station else None,
            'site': self.site if self.site else None,
            'agencies': self.agencies,
            'SiteLogStatus': SiteLogStatus,
            'is_moderator': self.site.is_moderator(
                self.request.user
            ) if self.site else None,
            # some non-moderators may be able to publish a some changes
            'can_publish': self.site.can_publish(
                self.request.user
            ) if self.site else None,
            'link_view': 'slm:edit'
            if self.request.resolver_match.view_name not in {
                'slm:alerts',
                'slm:download',
                'slm:review',
                'slm:log',
                'slm:edit'
            } else self.request.resolver_match.view_name,
            'station_alert_level': AlertLevel(max_alert) if max_alert else None
        })
        if self.station:
            try:
                self.station = Site.objects.get(name=context['station'])
                if (
                    not self.request.user.is_superuser and
                    self.station not in self.sites
                ):
                    raise PermissionDenied()
            except Site.DoesNotExist:
                raise Http404(f'Site {context["station"]} was not found!')
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

    template_name = 'slm/station/edit.html'

    FORMS = {
        form.section_name().lower().replace(' ', ''): form
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
            SiteMoreInformationForm
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
        try:
            site = Site.objects.editable_by(self.request.user).get(
                name__iexact=kwargs.get('station')
            )
        except Site.DoesNotExist:
            raise Http404(
                f'Station {kwargs.get("station", "")} does not exist!'
            )

        root_status = (
            SiteLogStatus.PUBLISHED if site.status == SiteLogStatus.UPDATED
            else site.status
        )

        context = super().get_context_data(**kwargs)
        context.update({
            'section_id': kwargs.get('section', None),
            'sections': {},
            'forms': []
        })

        section = self.FORMS.get(kwargs.get('section', None), None)
        if section:
            context['section_name'] = section.section_name()
            context['multi'] = issubclass(section._meta.model, SiteSubSection)

        # create the context of our form tree - the form/edit templates are
        # responsible for rendering this structure in html
        for section_id, form in self.FORMS.items():
            if hasattr(form, 'NAV_HEADING'):
                context['sections'].setdefault(
                    form.NAV_HEADING,
                    {
                        'id': form.group_name(),
                        'flags': 0,
                        'status': SiteLogStatus.EMPTY,
                        'active': False,
                        'subsections': {}
                    }
                )['subsections'][form.section_name()] = {
                    'id': form.section_name().lower().replace(' ', ''),
                    'group': form.group_name(),  # todo remove
                    'parent': form.group_name(),
                    'flags': 0,
                    'active': False,
                    'status': SiteLogStatus.EMPTY
                }
                if section is form:
                    context['parent'] = form.group_name()

            else:
                context['sections'][form.section_name()] = {
                    'id': form.section_name().lower().replace(' ', ''),
                    'flags': 0,
                    'status': SiteLogStatus.EMPTY
                }

            if issubclass(form._meta.model, SiteSubSection):
                # for subsections we need to:
                #   1) set nav heading meta information
                #   2) add sections for all children
                #   3) populate the subsections of the requested edit form

                heading = context['sections'][
                    getattr(form, 'NAV_HEADING', form.section_name())
                ]
                subheading = None
                if hasattr(form, 'NAV_HEADING'):
                    subheading = heading['subsections'][form.section_name()]

                for inst in reversed(
                    form._meta.model.objects.station(self.station).head()
                ):
                    if inst.published and inst.is_deleted:
                        continue  # elide deleted instances if published

                    if section is form:
                        # if this is our requested form for editing - populate
                        # it with data from head
                        context['forms'].append(
                            form(
                                instance=inst,
                                initial={
                                    field: getattr(inst, field)
                                    for field in form._meta.fields
                                }
                            )
                        )

                    heading['flags'] += inst.num_flags if inst else 0
                    heading['status'] = heading.get(
                        'status',
                        inst.mod_status
                    ).merge(inst.mod_status)
                    if subheading:
                        subheading.setdefault('flags', 0)
                        subheading['flags'] += inst.num_flags if inst else 0
                        subheading['status'] = subheading.get(
                            'status', inst.mod_status
                        ).merge(inst.mod_status)


                if section is form:
                    # if this is the edit section we add an empty form as the
                    # first form in the context, the template knows to render
                    # this form as the 'add' subsection form
                    context['forms'].insert(
                        0, form(initial={'site': self.station})
                    )
                    heading['active'] = heading.get('active', True) | True
                    if subheading:
                        subheading['active'] = True

            else:
                instance = form._meta.model.objects.station(
                    self.station
                ).head()  # we always edit on head
                if section is form:
                    # only one form is requested per edit view request - if
                    # this section is that form we need to populate it with
                    # data
                    context['forms'].append(
                        form(
                            instance=instance,
                            initial={
                                field: getattr(instance, field, None)
                                for field in form._meta.fields
                            } if instance else {'site': self.station}
                        )
                    )
                    context['sections'][form.section_name()]['active'] = True

                # for all sections we need to set status and number of flags
                context['sections'][
                    form.section_name()
                ]['flags'] = instance.num_flags if instance else 0
                context['sections'][
                    form.section_name()
                ]['status'] = (
                    instance.mod_status if instance
                    else SiteLogStatus.EMPTY
                )

        return context


class AlertsView(StationContextView):
    template_name = 'slm/station/alerts.html'


class UploadView(SLMView):
    template_name = 'slm/upload.html'


class NewSiteView(StationContextView):
    template_name = 'slm/new_site.html'

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        data = {
            field: request.POST[field]
            for field in NewSiteForm._meta.fields if field in request.POST
        }
        if data.get('agencies', None):
            data['agencies'] = [
                Agency.objects.get(pk=int(agency))
                for agency in [data['agencies']]
            ]
        data['name'] = data['name'].upper()
        if not request.user.is_superuser:
            for agency in data['agencies']:
                if request.user.agency != agency:
                    raise PermissionDenied(
                        'Only allowed to create new sites for your agency.'
                    )

        new_site = NewSiteForm(data)
        if new_site.is_bound and new_site.is_valid():
            new_site.save()
            slm_signals.site_proposed.send(
                sender=self,
                site=new_site.instance,
                user=request.user,
                timestamp=new_site.instance.created,
                request=request,
                agencies=data['agencies']
            )
            return redirect(
                to=reverse(
                    'slm:edit',
                    kwargs={'station': new_site.instance.name}
                )
            )

        context = super().get_context_data(**kwargs)
        context['form'] = new_site
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = NewSiteForm(
            initial={
                'agencies': Agency.objects.filter(
                    id=self.request.user.agency.id
                )} if not self.request.user.is_superuser else {}
        )
        if not self.request.user.is_superuser:
            context['form'].fields["agencies"].queryset = \
                Agency.objects.filter(id=self.request.user.agency.id)
        return context


class IndexView(StationContextView):
    template_name = 'slm/station/base.html'


class DownloadView(StationContextView):
    template_name = 'slm/station/download.html'


class UserProfileView(SLMView):
    template_name = 'slm/profile.html'
    success_url = reverse_lazy('profile')

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return self.render_to_response({
            'user_form': UserForm(instance=request.user),
            'profile_form': UserProfileForm(instance=request.user.profile)
        })

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        user_form = UserForm(
            {
                field: request.POST[field]
                for field in UserForm._meta.fields
                if field in request.POST
            },
            instance=request.user
        )
        if not request.user.profile:
            request.user.profile = UserProfile.objects.create()

        profile_form = UserProfileForm(
            {
                field: request.POST[field]
                for field in UserProfileForm._meta.fields
                if field in request.POST
            },
            instance=request.user.profile
        )

        if user_form.is_bound and user_form.is_valid():
            user_form.save()

        import pdb
        pdb.set_trace()
        if profile_form.is_bound and profile_form.is_valid():
            profile_form.save()

        return self.render_to_response(
            {'user_form': user_form, 'profile_form': profile_form}
        )


class LogView(StationContextView):

    template_name = 'slm/station/log.html'


class UserActivityLogView(SLMView):

    template_name = 'slm/user_activity.html'

    def get_context_data(self, log_user=None, **kwargs):
        context = super().get_context_data()
        try:
            if log_user:
                # must be a super user to see other people's log history
                # todo configurable perm for this? like is mod for user's
                #  agency?
                if not self.request.user.is_superuser:
                    raise PermissionDenied()

                context['log_user'] = get_user_model().objects.get(pk=log_user)
            else:
                # otherwise we're getting the logged in user's log history
                context['log_user'] = self.request.user

        except get_user_model().DoesNotExist:
            raise Http404()

        return context


class StationReviewView(StationContextView):

    template_name = 'slm/station/review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        def parse_time(timestamp):
            if timestamp:
                return datetime.fromisoformat(timestamp)
            return timestamp

        epoch = kwargs.get('epoch', None)
        published = (
            True if to_bool(self.request.GET.get('pub', True))
            else None
        )
        back_t = parse_time(self.request.GET.get('back', None))
        forward_t = parse_time(self.request.GET.get('forward', None))
        log_entries = LogEntry.objects.filter(
            site=self.station
        ).prefetch_related('site_log_object')

        pub_q = Q()
        if published:
            pub_q = Q(type=LogEntryType.PUBLISH)

        forward_inst = SiteLogSerializer(
            instance=self.station, epoch=forward_t or epoch, published=None
        )
        forward_text = forward_inst.text

        if not published and not back_t:
            back_t = log_entries.filter(
                Q(epoch__lt=forward_inst.epoch)
            ).aggregate(Max('epoch'))['epoch__max']

        back_inst = SiteLogSerializer(
            instance=self.station, epoch=back_t or epoch, published=published
        )
        back_text = back_inst.text

        forward_prev = log_entries.filter(
            Q(epoch__lt=forward_inst.epoch) &
            Q(epoch__gt=back_inst.epoch) &
            pub_q
        ).order_by('-timestamp').first()

        forward_next = log_entries.filter(
            Q(epoch__gt=forward_inst.epoch) &
            pub_q
        ).order_by('timestamp').first()

        back_prev = log_entries.filter(
            Q(epoch__lt=back_inst.epoch) &
            pub_q
        ).order_by('-timestamp').first()

        back_next = log_entries.filter(
            Q(epoch__lt=forward_inst.epoch) &
            Q(epoch__gt=back_inst.epoch) &
            pub_q
        ).order_by('timestamp').first()

        context.update({
            'forward_text': forward_text,
            'back_text': back_text,
            'unpublished_changes': not forward_inst.is_published,
            'forward_prev': forward_prev.epoch.isoformat()
            if forward_prev else None,
            'forward_current': forward_inst.epoch.isoformat(),
            'forward_next': forward_next.epoch.isoformat()
            if forward_next else None,
            'back_prev': back_prev.epoch.isoformat() if back_prev else None,
            'back_current': back_inst.epoch.isoformat(),
            'back_next': back_next.epoch.isoformat() if back_next else None,
            'published': published,
            'epoch': epoch.isoformat() if epoch else ''
        })
        return context


class AlertsView(SLMView):
    template_name = 'slm/alerts.html'
