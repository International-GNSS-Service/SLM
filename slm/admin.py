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
    Antenna,
    Receiver,
    Radome,
    Manufacturer,
    SiteFileUpload,
    Network
)
from slm.authentication import permissions
from allauth.account.models import EmailAddress


admin.site.unregister(Group)
#admin.site.unregister(EmailAddress)


class UserAgencyInline(admin.TabularInline):
    model = Agency.users.through
    extra = 0


class UserAdmin(BaseUserAdmin):

    # chooses which fields to display for admin users
    list_display = (
        'email', 'first_name', 'last_name', 'last_visit', 'is_superuser'
    )
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['last_visit', 'date_joined']

    inlines = [UserAgencyInline]

    ordering = ('-last_visit',)
    list_filter = ('is_superuser',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name',)}),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_superuser', 'groups', 'user_permissions'
            ),
        }),
        (_('Important dates'), {'fields': ('last_visit', 'date_joined')}),
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

    actions = ['request_password_reset']

    def request_password_reset(self, request, queryset):
        initiate_password_resets(queryset, request=request)

    request_password_reset.short_description = _(
        'Request password resets.'
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # remove all of the standard django object permissions from the admin
        # they are just clutter because we restrict access to the admin to
        # superusers. The only permissions that should be shown are permissions
        # specific the to the SLM
        form.base_fields['user_permissions'].queryset = permissions()
        return form


class GroupAdmin(BaseGroupAdmin):

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # remove all of the standard django object permissions from the admin
        # they are just clutter because we restrict access to the admin to
        # superusers. The only permissions that should be shown are permissions
        # specific the to the SLM
        form.base_fields['permissions'].queryset = permissions()
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
    inlines = [SiteAgencyInline, NetworkInline]
    exclude = ['agencies']


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class AgencyAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class AlertAdmin(admin.ModelAdmin):
    pass


class SatelliteSystemAdmin(admin.ModelAdmin):
    pass


class AntennaAdmin(admin.ModelAdmin):
    pass


class ReceiverAdmin(admin.ModelAdmin):
    pass


class RadomeAdmin(admin.ModelAdmin):
    pass


class ManufacturerAdmin(admin.ModelAdmin):
    pass


class SiteFileUploadAdmin(admin.ModelAdmin):

    search_fields = ['site__name']
    list_filter = ['file_type', 'log_format']


admin.site.register(get_user_model(), UserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Agency, AgencyAdmin)
admin.site.register(Alert, AlertAdmin)
admin.site.register(SatelliteSystem, SatelliteSystemAdmin)
admin.site.register(Antenna, AntennaAdmin)
admin.site.register(Receiver, ReceiverAdmin)
admin.site.register(Radome, RadomeAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(SiteFileUpload, SiteFileUploadAdmin)
