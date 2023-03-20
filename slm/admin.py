"""
Handles admin site for Django project.


NOTES:
This file essentially controls what is seen on the admin site
as well as overriding the default methods for adding
a new admin user. 

To add a new model group to admin site simply add 
"admin.site.register(NEW MODEL GROUP NAME)"
to bottom of file.

Same process can be applied for unregistering a model
group (same command with unregister).

More info:
https://docs.djangoproject.com/en/3.2/ref/contrib/admin/
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import (
    UserAdmin as BaseUserAdmin,
    GroupAdmin as BaseGroupAdmin
)
from django.contrib.auth.models import Group
from django.utils.translation import gettext as _
from slm.authentication import initiate_password_resets
from slm.models import (
    Agency,
    SatelliteSystem,
    Site,
    Alert,
    UserAlert,
    AntCal,
    SiteReceiver,
    GeodesyMLInvalid,
    ReviewRequested,
    UpdatesRejected,
    AgencyAlert,
    SiteAlert,
    Antenna,
    Receiver,
    Radome,
    Manufacturer,
    SiteFileUpload,
    Network,
    UserProfile,
    Help,
    About,
    TideGauge,
    SiteTideGauge
)
from slm.authentication import permissions
from polymorphic.admin import (
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter
)
from django.conf import settings
from django.utils.safestring import mark_safe


admin.site.unregister(Group)


class UserAgencyInline(admin.TabularInline):
    model = Agency.users.through
    extra = 0


class TideGaugeInline(admin.TabularInline):
    model = TideGauge.sites.through
    extra = 0


class SiteTGInline(admin.TabularInline):
    model = Site.tide_gauges.through
    extra = 0


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):

    # chooses which fields to display for admin users
    list_display = (
        'email', 'first_name', 'last_name', 'last_activity', 'is_superuser'
    )
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['last_activity', 'date_joined']

    inlines = [UserAgencyInline, ProfileInline]

    ordering = ('-last_activity',)
    list_filter = ('is_superuser', 'html_emails', 'silence_alerts')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name',)}),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_superuser', 'groups', 'user_permissions'
            ),
        }),
        (_('Preferences'), {'fields': ('silence_alerts', 'html_emails')}),
        (_('Important Dates'), {'fields': ('last_activity', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'is_superuser',
                'password1', 'password2'
            ),
        }),
    )

    actions = ['request_password_reset', 'enable_emails', 'disable_emails']

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

    def request_password_reset(self, request, queryset):
        initiate_password_resets(queryset, request=request)
    request_password_reset.short_description = _('Request password resets.')

    def enable_emails(self, request, queryset):
        queryset.update(silence_alerts=False)
    enable_emails.short_description = _('Enable alert emails for users.')

    def disable_emails(self, request, queryset):
        queryset.update(silence_alerts=True)
    disable_emails.short_description = _('Disable alert emails for users.')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # remove all of the standard django object permissions from the admin
        # they are just clutter because we restrict access to the admin to
        # superusers. The only permissions that should be shown are permissions
        # specific the to the SLM
        user_permissions = form.base_fields.get('user_permissions', None)
        if user_permissions:
            user_permissions.queryset = permissions()
        silence_alerts = form.base_fields.get('silence_alerts')
        if silence_alerts is not None:
            silence_alerts.initial = getattr(
            settings, 'SLM_EMAILS_REQUIRE_LOGIN', True
        )
        return form


class GroupAdmin(BaseGroupAdmin):

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # remove all of the standard django object permissions from the admin
        # they are just clutter because we restrict access to the admin to
        # superusers. The only permissions that should be shown are permissions
        # specific the to the SLM
        permissions_field = form.base_fields.get('permissions', None)
        if permissions_field:
            permissions_field.queryset = permissions()
        return form


class NetworkInline(admin.TabularInline):
    model = Network.sites.through
    extra = 0


class SiteAgencyInline(admin.TabularInline):
    model = Agency.sites.through
    extra = 0


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):

    search_fields = ('name',)
    inlines = [SiteAgencyInline, NetworkInline, TideGaugeInline]
    exclude = ['agencies']


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class AgencyAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class SatelliteSystemAdmin(admin.ModelAdmin):
    pass


class AntennaAdmin(admin.ModelAdmin):

    search_fields = ('name',)
    list_filter = ('state',)


class ReceiverAdmin(admin.ModelAdmin):

    search_fields = ('name',)
    list_filter = ('state',)


class RadomeAdmin(admin.ModelAdmin):

    search_fields = ('name',)
    list_filter = ('state',)


class TideGaugeAdmin(admin.ModelAdmin):

    search_fields = ('name', 'sonel_id')
    list_display = ('name', 'sonel_link')
    inlines = [SiteTGInline]

    def sonel_link(self,obj):
        return mark_safe(
            f'<a href="{obj.sonel_link}" target="_blank">{obj.sonel_link}</a>'
        )

    def get_queryset(self, request):
        return self.model.objects.prefetch_related('sites')


class AntennaCalibrationAdmin(admin.ModelAdmin):
    search_fields = ('antenna__model', 'radome__model')
    list_display = ('antenna', 'radome', 'method_label', 'calibrated')
    list_filter = ('method',)

    def method_label(self, obj):
        return str(obj.method.label)

    def get_queryset(self, request):
        return self.model.objects.select_related('antenna', 'radome')


class ManufacturerAdmin(admin.ModelAdmin):
    pass


class HelpAdmin(admin.ModelAdmin):
    pass


class AboutAdmin(admin.ModelAdmin):
    pass


class SiteFileUploadAdmin(admin.ModelAdmin):

    search_fields = ['site__name']
    list_filter = ['file_type', 'log_format']


class AlertAdminMixin:

    actions = ['send_emails']

    def send_emails(self, request, queryset):
        queryset.send_emails(request)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['issuer'].initial = request.user
        form.base_fields['issuer'].disabled = True
        form.base_fields['issuer'].widget.can_change_related = False
        form.base_fields['issuer'].widget.can_delete_related = False
        form.base_fields['issuer'].widget.can_add_related = False
        form.base_fields['priority'].initial = getattr(
            self.model,
            'DEFAULT_PRIORITY',
            0
        )
        return form


class AlertChildAdmin(AlertAdminMixin, PolymorphicChildModelAdmin):
    base_model = Alert


@admin.register(UserAlert)
class UserAlertAdmin(AlertChildAdmin):
    base_model = UserAlert
    show_in_index = True


@admin.register(SiteAlert)
class SiteAlertAdmin(AlertChildAdmin):
    base_model = SiteAlert
    show_in_index = True


@admin.register(AgencyAlert)
class AgencyAlertAdmin(AlertChildAdmin):
    base_model = AgencyAlert
    show_in_index = True


@admin.register(GeodesyMLInvalid)
class GeodesyMLInvalidAdmin(AlertChildAdmin):
    base_model = GeodesyMLInvalid
    show_in_index = True


@admin.register(ReviewRequested)
class ReviewRequestedAdmin(AlertChildAdmin):
    base_model = ReviewRequested
    show_in_index = True


@admin.register(UpdatesRejected)
class UpdatesRejectedAdmin(AlertChildAdmin):
    base_model = UpdatesRejected
    show_in_index = True


@admin.register(Alert)
class AlertAdmin(AlertAdminMixin, PolymorphicParentModelAdmin):
    """ The parent alert model admin """
    base_model = Alert
    child_models = (
        Alert,
        UserAlert,
        SiteAlert,
        AgencyAlert,
        GeodesyMLInvalid,
        ReviewRequested,
        UpdatesRejected
    )
    list_filter = (PolymorphicChildModelFilter,)

"""
class SLMAdminSite(admin.AdminSite):

    def get_app_list(self, request, app_label=None):
        #Return a sorted list of all the installed apps that have been
        #registered in this site.
        ret = super().get_app_list(request, app_label=app_label)

        # force group all alerts together
        spoofed_alerts_app = {
            'app_label': 'slm_alerts',
            'app_url': '/admin/slm/alerts/',
            'has_module_perms': True,
            'models': [],
            'name': 'SLM Alerts'
        }

        for app in ret:
            models = []
            for model in app['models']:
                if issubclass(model['model'], Alert):
                    spoofed_alerts_app['models'].append(model)
                else:
                    models.append(model)
            app['models'] = models

        ret.insert(1, spoofed_alerts_app)
        return ret
"""

#admin.site = SLMAdminSite()

admin.site.register(get_user_model(), UserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Agency, AgencyAdmin)
admin.site.register(TideGauge, TideGaugeAdmin)
admin.site.register(SatelliteSystem, SatelliteSystemAdmin)
admin.site.register(Antenna, AntennaAdmin)
admin.site.register(Receiver, ReceiverAdmin)
admin.site.register(Radome, RadomeAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(SiteFileUpload, SiteFileUploadAdmin)
admin.site.register(Help, HelpAdmin)
admin.site.register(About, AboutAdmin)
admin.site.register(AntCal, AntennaCalibrationAdmin)

admin.autodiscover()
